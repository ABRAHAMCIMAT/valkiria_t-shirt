"""
Epic Estimation Models
======================
Contains ML models for estimating:
- Story Points
- Sprint Duration (Time)
- Cost
- Effort

Models use ensemble of RandomForest and DecisionTree regressors.
Also includes semantic similarity-based estimation using embeddings.
"""

import pickle
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class EstimationModels:
    """Manages ensemble models for epic estimation."""

    def __init__(self, model_dir: str = "trained_models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)

        # Model components (to be trained)
        self.rf_models = {}  # RandomForest models
        self.dt_models = {}  # DecisionTree models
        self.scaler = StandardScaler()
        self.features_columns = None

        # Model metrics (R² scores)
        self.model_metrics = {}  # Store R² and other metrics for each target

        # Embeddings
        self.embedding_model = None
        self.embeddings = None
        self.corpus_texts = None
        self.corpus_points = None

        # Target variables
        self.targets = ["point", "time", "cost", "effort"]

    def prepare_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        Prepare data for model training.

        Args:
            df: DataFrame with all features and targets

        Returns:
            X: Feature matrix (n_samples, n_features)
            y_dict: Dictionary with target arrays for each estimation type
        """
        # Feature columns (exclude targets)
        targets_cols = [
            'Custom field (Story Points)',
            'Duracion_Sprint',
            'Costo_por_dia',
            'Esfuerzo_por_Puntos_Historia'
        ]

        self.features_columns = [col for col in df.columns if col not in targets_cols]

        # Prepare X matrix
        X = df[self.features_columns].values

        # Prepare y dictionaries
        y_dict = {}
        if 'Custom field (Story Points)' in df.columns:
            y_dict['point'] = df['Custom field (Story Points)'].values
        if 'Duracion_Sprint' in df.columns:
            y_dict['time'] = df['Duracion_Sprint'].values
        if 'Costo_por_dia' in df.columns:
            y_dict['cost'] = df['Costo_por_dia'].values
        if 'Esfuerzo_por_Puntos_Historia' in df.columns:
            y_dict['effort'] = df['Esfuerzo_por_Puntos_Historia'].values

        return X, y_dict

    def train(self, X: np.ndarray, y_dict: Dict[str, np.ndarray],
              test_size: float = 0.2, random_state: int = 42):
        """
        Train ensemble models for all targets.

        Args:
            X: Feature matrix
            y_dict: Dictionary with target arrays
            test_size: Test set proportion
            random_state: Random seed for reproducibility
        """
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)

        for target, y in y_dict.items():
            print(f"\n{'='*60}")
            print(f"Training models for {target.upper()}")
            print(f"{'='*60}")

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=test_size, random_state=random_state
            )

            # Train RandomForest
            print(f"Training RandomForest for {target}...")
            rf_model = RandomForestRegressor(
                max_depth=70,
                max_features='log2',
                n_estimators=200,
                random_state=random_state,
                n_jobs=-1
            )
            rf_model.fit(X_train, y_train)
            y_pred_rf = rf_model.predict(X_test)
            r2_rf = r2_score(y_test, y_pred_rf)

            # Train DecisionTree
            print(f"Training DecisionTree for {target}...")
            dt_params = {
                'point': {'max_depth': 30, 'min_samples_leaf': 2, 'min_samples_split': 10},
                'time': {'max_depth': 20},
                'cost': {'max_depth': 20},
                'effort': {'max_depth': 20}
            }

            dt_model = DecisionTreeRegressor(
                random_state=random_state,
                **dt_params.get(target, {})
            )
            dt_model.fit(X_train, y_train)
            y_pred_dt = dt_model.predict(X_test)
            r2_dt = r2_score(y_test, y_pred_dt)

            # Ensemble predictions
            y_pred_ensemble = (y_pred_rf + y_pred_dt) / 2

            # Evaluate all models
            mae = mean_absolute_error(y_test, y_pred_ensemble)
            mse = mean_squared_error(y_test, y_pred_ensemble)
            r2_ensemble = r2_score(y_test, y_pred_ensemble)

            print(f"Ensemble Metrics for {target}:")
            print(f"  MAE: {mae:.4f}")
            print(f"  MSE: {mse:.4f}")
            print(f"  R²: {r2_ensemble:.4f}")
            print("Individual R² Scores:")
            print(f"  RandomForest R²: {r2_rf:.4f}")
            print(f"  DecisionTree R²: {r2_dt:.4f}")

            # Store models
            self.rf_models[target] = rf_model
            self.dt_models[target] = dt_model

            # Store metrics
            if target not in self.model_metrics:
                self.model_metrics[target] = {}

            self.model_metrics[target] = {
                'ensemble': float(r2_ensemble),
                'random_forest': float(r2_rf),
                'decision_tree': float(r2_dt),
                'mae': float(mae),
                'mse': float(mse)
            }

    def predict(self, X: np.ndarray, target: str = 'point') -> Dict[str, float]:
        """
        Make predictions using ensemble model.

        Args:
            X: Feature matrix (1 or more samples)
            target: Target type ('point', 'time', 'cost', 'effort')

        Returns:
            Dictionary with predictions and statistics
        """
        if target not in self.rf_models:
            raise ValueError(f"No model trained for target: {target}")

        # Scale input
        X_scaled = self.scaler.transform(X)

        # Get predictions from both models
        y_pred_rf = self.rf_models[target].predict(X_scaled)
        y_pred_dt = self.dt_models[target].predict(X_scaled)

        # Ensemble prediction
        y_pred_ensemble = (y_pred_rf + y_pred_dt) / 2

        return {
            'ensemble': y_pred_ensemble,
            'random_forest': y_pred_rf,
            'decision_tree': y_pred_dt
        }

    def load_embeddings_model(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """Load sentence transformer for semantic similarity."""
        if not EMBEDDINGS_AVAILABLE:
            print("Warning: SentenceTransformer not available. Semantic similarity features disabled.")
            return

        print(f"Loading embeddings model: {model_name}")
        self.embedding_model = SentenceTransformer(model_name)

    def build_semantic_corpus(self, corpus_texts: List[str], corpus_points: np.ndarray):
        """
        Build semantic embedding corpus for similarity-based estimation.

        Args:
            corpus_texts: List of historical story descriptions
            corpus_points: Array of corresponding story points
        """
        if self.embedding_model is None:
            self.load_embeddings_model()

        if self.embedding_model is None:
            print("Cannot build embeddings corpus without SentenceTransformer")
            return

        print(f"Encoding {len(corpus_texts)} texts for semantic similarity...")
        self.embeddings = self.embedding_model.encode(
            corpus_texts,
            batch_size=256,
            show_progress_bar=True,
            normalize_embeddings=True
        ).astype(np.float32)

        self.corpus_texts = corpus_texts
        self.corpus_points = corpus_points.astype(np.float32)

        print(f"Corpus embeddings shape: {self.embeddings.shape}")

    def estimate_by_similarity(self, text: str, k: int = 30) -> Dict[str, float]:
        """
        Estimate story points using semantic similarity to historical data.

        Args:
            text: Story description text
            k: Number of similar stories to consider

        Returns:
            Dictionary with estimation metrics
        """
        if self.embeddings is None:
            raise ValueError("Semantic corpus not built. Call build_semantic_corpus first.")

        # Encode query
        q = self.embedding_model.encode(
            [text],
            normalize_embeddings=True
        ).astype(np.float32)[0]

        # Compute cosine similarity
        sims = self.embeddings @ q

        # Get top-k similar stories
        top_indices = np.argsort(-sims)[:k]
        top_sims = sims[top_indices]
        top_points = self.corpus_points[top_indices]

        # Calculate weighted average
        p50 = np.percentile(top_points, 50)
        p85 = np.percentile(top_points, 85)

        # Round to Fibonacci
        fib_estimate = self._nearest_fibonacci(p50)

        return {
            'p50': float(p50),
            'p85': float(p85),
            'fib': float(fib_estimate),
            'top_sim': float(top_sims[0]),
            'top_points': float(top_points[0]),
            'k_used': k
        }

    @staticmethod
    def _nearest_fibonacci(x: float) -> float:
        """Round to nearest Fibonacci number."""
        fib = np.array([1, 2, 3, 5, 8, 13, 21, 34], dtype=np.float32)
        if x <= 0:
            return 0.0
        return float(fib[np.argmin(np.abs(fib - x))])

    def save(self, filepath: str = None):
        """Save models to disk."""
        if filepath is None:
            filepath = self.model_dir / "models.pkl"

        state = {
            'rf_models': self.rf_models,
            'dt_models': self.dt_models,
            'scaler': self.scaler,
            'features_columns': self.features_columns,
            'embedding_model': self.embedding_model if EMBEDDINGS_AVAILABLE else None,
            'embeddings': self.embeddings,
            'corpus_texts': self.corpus_texts,
            'corpus_points': self.corpus_points,
            'model_metrics': self.model_metrics
        }

        with open(filepath, 'wb') as f:
            pickle.dump(state, f)

        print(f"Models saved to {filepath}")

    def load(self, filepath: str = None):
        """Load models from disk."""
        if filepath is None:
            filepath = self.model_dir / "models.pkl"

        with open(filepath, 'rb') as f:
            state = pickle.load(f)

        self.rf_models = state['rf_models']
        self.dt_models = state['dt_models']
        self.scaler = state['scaler']
        self.features_columns = state['features_columns']
        self.embedding_model = state.get('embedding_model')
        self.embeddings = state.get('embeddings')
        self.corpus_texts = state.get('corpus_texts')
        self.corpus_points = state.get('corpus_points')
        self.model_metrics = state.get('model_metrics', {})

        print(f"Models loaded from {filepath}")
