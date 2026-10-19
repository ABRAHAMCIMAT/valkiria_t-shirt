"""
FastAPI backend for epic estimation.
Provides REST endpoints for:
- Model training
- Batch prediction from Excel
- Single story estimation
- Model statistics
"""

import os

# Import our custom modules
import sys
import tempfile
import traceback
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.epic_estimation_models import EstimationModels
from services.multi_agent import MultiAgentEstimator
from services.workbook_service import WorkbookKnowledgeBase
from utils.data_preprocessing import JiraDataPreprocessor, process_user_excel

# ============================================================================
# Request/Response Models
# ============================================================================

class StoryEstimationRequest(BaseModel):
    """Request for estimating a single story."""
    title: str
    description: str
    acceptance_criteria: Optional[List[str]] = None
    priority: Optional[str] = None
    issue_type: Optional[str] = None


class BatchEstimationRequest(BaseModel):
    """Request for batch estimation (used for Excel processing)."""
    stories: List[StoryEstimationRequest]


class EstimationResponse(BaseModel):
    """Response with estimation results."""
    story_title: str
    point_estimate: Dict[str, float]  # ensemble, random_forest, decision_tree
    time_estimate: Dict[str, float]
    cost_estimate: Dict[str, float]
    effort_estimate: Dict[str, float]
    semantic_estimate: Optional[Dict[str, float]] = None
    model_confidence: Optional[Dict[str, Dict[str, float]]] = None  # R² scores


class ModelStatsResponse(BaseModel):
    """Response with model statistics."""
    models_trained: bool
    targets: List[str]
    training_samples: Optional[int]
    features_count: Optional[int]
    model_location: str
    model_metrics: Optional[Dict[str, Dict[str, float]]] = None  # R² and other metrics


class ChatRequest(BaseModel):
    message: str


class RoleRequest(BaseModel):
    name: str
    area: str = ""
    required: bool = True
    collaborators: float = 1
    cost_hourly: float = 0
    source_cost: float = 0
    source_basis: str = "hora"
    source_row: int = 0


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Epic Estimation API",
    description="ML-based API for estimating story points, time, cost, and effort",
    version="1.0.0"
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
estimation_models: Optional[EstimationModels] = None
jira_data_preprocessor: Optional[JiraDataPreprocessor] = None
training_in_progress = False

# Configuration
MODEL_DIR = Path(__file__).parent.parent / "trained_models"
MODEL_DIR.mkdir(exist_ok=True)
MODEL_FILE = MODEL_DIR / "models.pkl"
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)
knowledge_base = WorkbookKnowledgeBase(DATA_DIR / "knowledge")
latest_analysis: Optional[Dict] = None


# ============================================================================
# Startup and Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize models on startup."""
    global estimation_models

    print("Starting up Epic Estimation API...")

    # Try to load existing models
    if MODEL_FILE.exists():
        try:
            estimation_models = EstimationModels(str(MODEL_DIR))
            estimation_models.load(str(MODEL_FILE))
            print(f"[OK] Loaded existing models from {MODEL_FILE}")
        except Exception as e:
            print(f"[ERROR] Failed to load models: {e}")
            print("  Models will need to be trained before predictions can be made")
    else:
        print("[INFO] No trained models found")
        bundled_training = Path(__file__).parent.parent / "training_data_improved.csv"
        if bundled_training.exists():
            try:
                estimation_models = _train_bundled_models(bundled_training)
                print(f"[OK] Modelos base entrenados con {bundled_training.name}")
            except Exception as exc:
                print(f"[ERROR] No fue posible entrenar los modelos base: {exc}")
        else:
            print("  Call POST /train endpoint with JIRA CSV to train models")

    bundled_template = DATA_DIR / "T-Shirt_template.xlsx"
    if not knowledge_base.load() and bundled_template.exists():
        knowledge_base.ingest(bundled_template)
        print(f"[OK] Base de conocimiento creada desde {bundled_template.name}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("Shutting down Epic Estimation API...")


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "models_loaded": estimation_models is not None and bool(estimation_models.rf_models),
        "knowledge_loaded": bool(knowledge_base.chunks),
        "timestamp": pd.Timestamp.now().isoformat()
    }


# ============================================================================
# Model Training Endpoints
# ============================================================================

@app.post("/train")
async def train_models(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Train models from CSV file.

    Required CSV columns at minimum:
    - Custom field (Story Points) [target variable]
    - Duracion_Sprint, Costo_por_dia, Esfuerzo_por_Puntos_Historia [optional]
    """
    global estimation_models, training_in_progress

    if training_in_progress:
        raise HTTPException(
            status_code=429,
            detail="Training already in progress"
        )

    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="File must be CSV format"
        )

    training_in_progress = True

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix='.csv',
            mode='wb'
        ) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Train models
            print(f"Training models from {file.filename}...")

            # Read CSV and prepare data
            df = pd.read_csv(tmp_path, encoding='utf-8')
            df.columns = df.columns.str.strip()

            print(f"[INFO] Loaded {len(df)} rows with columns: {df.columns.tolist()}")

            # Required columns: target plus the text columns feature
            # extraction is based on
            required_col = 'Custom field (Story Points)'
            text_cols = ['Titulo', 'Historia de Usuario', 'Criterios de Aceptación']

            if required_col not in df.columns:
                raise ValueError(f"Missing required column: {required_col}")

            missing_text_cols = [c for c in text_cols if c not in df.columns]
            if missing_text_cols:
                raise ValueError(f"Missing required columns for feature extraction: {missing_text_cols}")

            # Drop rows with missing target
            df = df.dropna(subset=[required_col])

            if len(df) < 10:
                raise ValueError(f"Not enough data: {len(df)} rows after cleaning")

            # Build the same 10-feature linguistic vector used at prediction
            # time, so the trained scaler/models match what /estimate/* sends
            X_features = []
            for _, row in df.iterrows():
                criteria_raw = row.get('Criterios de Aceptación', '')
                criteria_list = []
                if pd.notna(criteria_raw) and isinstance(criteria_raw, str):
                    criteria_list = [c.strip() for c in criteria_raw.split('\n') if c.strip()]

                story_req = StoryEstimationRequest(
                    title=str(row.get('Titulo', '')),
                    description=str(row.get('Historia de Usuario', '')),
                    acceptance_criteria=criteria_list or None
                )
                X_features.append(create_feature_vector(story_req)[0])

            X = np.array(X_features, dtype=np.float32)

            # Prepare targets: use the real sprint/cost/effort columns when
            # available, falling back to synthetic values only if absent
            y_points = df[required_col].values.astype(np.float32)

            if 'Duracion_Sprint' in df.columns:
                y_time = df['Duracion_Sprint'].fillna(df['Duracion_Sprint'].median()).values.astype(np.float32)
            else:
                y_time = y_points * np.random.uniform(0.8, 1.2, len(y_points))

            if 'Costo_por_dia' in df.columns:
                y_cost = df['Costo_por_dia'].fillna(df['Costo_por_dia'].median()).values.astype(np.float32)
            else:
                y_cost = y_points * np.random.uniform(200, 400, len(y_points))

            if 'Esfuerzo_por_Puntos_Historia' in df.columns:
                y_effort = df['Esfuerzo_por_Puntos_Historia'].fillna(df['Esfuerzo_por_Puntos_Historia'].median()).values.astype(np.float32)
            else:
                y_effort = y_points * np.random.uniform(4, 16, len(y_points))

            y_dict = {
                'point': y_points,
                'time': y_time,
                'cost': y_cost,
                'effort': y_effort
            }

            # Create and train models
            estimation_models = EstimationModels(str(MODEL_DIR))
            estimation_models.train(X, y_dict)
            estimation_models.save(str(MODEL_FILE))

            print("[OK] Models trained successfully")

            return {
                "status": "success",
                "message": f"Models trained on {len(df)} samples",
                "models": list(estimation_models.rf_models.keys()),
                "model_file": str(MODEL_FILE)
            }

        finally:
            # Clean up temp file
            os.unlink(tmp_path)

    except Exception as e:
        print(f"Error during training: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Training failed: {str(e)}"
        )

    finally:
        training_in_progress = False


# ============================================================================
# Prediction Endpoints
# ============================================================================

@app.post("/estimate/single", response_model=EstimationResponse)
async def estimate_single_story(request: StoryEstimationRequest):
    """Estimate a single story."""
    if not estimation_models or not estimation_models.rf_models:
        raise HTTPException(
            status_code=503,
            detail="Models not trained. Call POST /train first."
        )

    try:
        # Create feature vector from story
        # This is a simplified version; in production, you'd encode all features
        features = create_feature_vector(request)

        # Make predictions
        point_pred = estimation_models.predict(features, 'point')
        time_pred = estimation_models.predict(features, 'time')
        cost_pred = estimation_models.predict(features, 'cost')
        effort_pred = estimation_models.predict(features, 'effort')

        # Try semantic estimation if corpus available
        semantic = None
        if estimation_models.embeddings is not None:
            try:
                text = f"{request.title}\n{request.description}"
                semantic = estimation_models.estimate_by_similarity(text)
            except Exception:
                pass

        # Get model confidence metrics (R² scores)
        model_confidence = None
        if hasattr(estimation_models, 'model_metrics') and estimation_models.model_metrics:
            model_confidence = {
                'point': estimation_models.model_metrics.get('point', {}),
                'time': estimation_models.model_metrics.get('time', {}),
                'cost': estimation_models.model_metrics.get('cost', {}),
                'effort': estimation_models.model_metrics.get('effort', {})
            }

        # Format response
        return EstimationResponse(
            story_title=request.title,
            point_estimate={
                'ensemble': float(point_pred['ensemble'][0]),
                'random_forest': float(point_pred['random_forest'][0]),
                'decision_tree': float(point_pred['decision_tree'][0])
            },
            time_estimate={
                'ensemble': float(time_pred['ensemble'][0]),
                'random_forest': float(time_pred['random_forest'][0]),
                'decision_tree': float(time_pred['decision_tree'][0])
            },
            cost_estimate={
                'ensemble': float(cost_pred['ensemble'][0]),
                'random_forest': float(cost_pred['random_forest'][0]),
                'decision_tree': float(cost_pred['decision_tree'][0])
            },
            effort_estimate={
                'ensemble': float(effort_pred['ensemble'][0]),
                'random_forest': float(effort_pred['random_forest'][0]),
                'decision_tree': float(effort_pred['decision_tree'][0])
            },
            semantic_estimate=semantic,
            model_confidence=model_confidence
        )

    except Exception as e:
        print(f"Error in estimation: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Estimation failed: {str(e)}"
        )


@app.post("/estimate/batch")
async def estimate_batch(request: BatchEstimationRequest):
    """Estimate multiple stories."""
    if not estimation_models or not estimation_models.rf_models:
        raise HTTPException(
            status_code=503,
            detail="Models not trained. Call POST /train first."
        )

    results = []
    errors = []

    for story in request.stories:
        try:
            result = await estimate_single_story(story)
            results.append(result)
        except Exception as e:
            errors.append({
                "story": story.title,
                "error": str(e)
            })

    return {
        "total": len(request.stories),
        "successful": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors if errors else None
    }


@app.post("/estimate/excel")
async def estimate_from_excel(file: UploadFile = File(...)):
    """
    Upload Excel file with stories and get estimations.

    Expected columns: Titulo, Historia de Usuario, Criterios de Aceptación
    """
    if not estimation_models or not estimation_models.rf_models:
        raise HTTPException(
            status_code=503,
            detail="Models not trained. Call POST /train first."
        )

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be Excel format (.xlsx or .xls)"
        )

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix='.xlsx',
            mode='wb'
        ) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        try:
            # Read Excel
            df = process_user_excel(tmp_path)

            # Convert to estimation requests
            requests = []
            for _, row in df.iterrows():
                criteria = row.get('Criterios de Aceptación', '')
                criteria_list = []
                if pd.notna(criteria):
                    if isinstance(criteria, str):
                        criteria_list = [c.strip() for c in criteria.split('\n') if c.strip()]
                    elif isinstance(criteria, list):
                        criteria_list = criteria

                requests.append(StoryEstimationRequest(
                    title=str(row.get('Titulo', 'Unknown')),
                    description=str(row.get('Historia de Usuario', '')),
                    acceptance_criteria=criteria_list if criteria_list else None
                ))

            # Get estimations
            batch_request = BatchEstimationRequest(stories=requests)
            result = await estimate_batch(batch_request)

            # Add Excel export capability
            result['export_url'] = '/estimate/excel/results'

            return result

        finally:
            os.unlink(tmp_path)

    except Exception as e:
        print(f"Error processing Excel: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Excel processing failed: {str(e)}"
        )


# ============================================================================
# Model Info Endpoints
# ============================================================================

@app.get("/models/stats", response_model=ModelStatsResponse)
async def get_model_stats():
    """Get statistics about trained models."""
    return ModelStatsResponse(
        models_trained=bool(estimation_models and estimation_models.rf_models),
        targets=list(estimation_models.rf_models.keys()) if estimation_models else [],
        training_samples=None,  # Would need to track during training
        features_count=len(estimation_models.features_columns) if estimation_models and estimation_models.features_columns else None,
        model_location=str(MODEL_FILE),
        model_metrics=estimation_models.model_metrics if estimation_models else None
    )


# ============================================================================
# Utility Functions
# ============================================================================

def create_feature_vector(request: StoryEstimationRequest) -> np.ndarray:
    """
    Create rich feature vector from story request.
    Extracts features from title, description, and criteria.
    """
    import re

    # Initialize 10-feature vector
    features = np.zeros((1, 10), dtype=np.float32)

    title = request.title or ''
    description = request.description or ''
    criteria = ' '.join(request.acceptance_criteria or [])
    full_text = f"{title} {description} {criteria}".lower()

    # Feature 0: Story complexity from title keywords
    complexity_keywords = ['complex', 'difícil', 'difícil', 'integración', 'integration',
                          'refactor', 'refactorización', 'arquitectura', 'architecture',
                          'seguridad', 'security', 'performance', 'database', 'api']
    complexity_score = sum(1 for kw in complexity_keywords if kw in full_text)
    features[0, 0] = min(complexity_score / 5.0, 1.0)

    # Feature 1: Story scope (text length normalized)
    text_length = len(description)
    features[0, 1] = min(text_length / 500.0, 1.0)

    # Feature 2: Number of acceptance criteria (indicates scope)
    criteria_count = len(request.acceptance_criteria or [])
    features[0, 2] = min(criteria_count / 5.0, 1.0)

    # Feature 3: Technical keywords (UI vs Backend vs Integration)
    tech_keywords = ['api', 'base de datos', 'database', 'backend', 'servidor',
                    'ui', 'frontend', 'interfaz', 'pantalla', 'screen', 'form',
                    'autenticación', 'authentication', 'cache', 'performance']
    tech_score = sum(1 for kw in tech_keywords if kw in full_text)
    features[0, 3] = min(tech_score / 4.0, 1.0)

    # Feature 4: Data/Integration keywords
    data_keywords = ['integración', 'integration', 'migración', 'migration', 'export',
                    'import', 'sync', 'sincronización', 'datos', 'data', 'csv', 'excel',
                    'api', 'rest', 'soap', 'webhook']
    data_score = sum(1 for kw in data_keywords if kw in full_text)
    features[0, 4] = min(data_score / 3.0, 1.0)

    # Feature 5: Testing requirements
    testing_keywords = ['test', 'prueba', 'unitario', 'unit', 'integration',
                       'validar', 'validación', 'verificar', 'qa']
    testing_score = sum(1 for kw in testing_keywords if kw in full_text)
    features[0, 5] = min(testing_score / 3.0, 1.0)

    # Feature 6: Priority encoding (from title hints)
    priority_keywords = {
        'urgent': 1.0, 'crítico': 1.0, 'critical': 1.0,
        'alta': 0.8, 'high': 0.8, 'importante': 0.8,
        'media': 0.5, 'medium': 0.5, 'normal': 0.5,
        'baja': 0.2, 'low': 0.2, 'menor': 0.2
    }
    priority_score = 0.5
    for kw, score in priority_keywords.items():
        if kw in full_text:
            priority_score = score
            break
    features[0, 6] = priority_score

    # Feature 7: Issue type hints
    type_keywords = {
        'feature': 0.8, 'característica': 0.8, 'nueva': 0.8,
        'bug': 0.4, 'error': 0.4, 'corrección': 0.4,
        'tarea': 0.3, 'task': 0.3, 'refactor': 0.6
    }
    type_score = 0.5
    for kw, score in type_keywords.items():
        if kw in full_text:
            type_score = score
            break
    features[0, 7] = type_score

    # Feature 8: Number words (estimation hints)
    numbers = re.findall(r'\d+', description)
    features[0, 8] = min(len(numbers) / 3.0, 1.0)

    # Feature 9: Unique word variety (simpler = more straightforward)
    words = description.split()
    if words:
        unique_ratio = len(set(words)) / max(len(words), 1)
        features[0, 9] = unique_ratio
    else:
        features[0, 9] = 0.5

    return features


def _train_bundled_models(csv_path: Path) -> EstimationModels:
    """Entrena automáticamente el modelo del repositorio en un primer arranque."""
    df = pd.read_csv(csv_path, encoding="utf-8").dropna(subset=["Custom field (Story Points)"])
    features = []
    for _, row in df.iterrows():
        criteria = str(row.get("Criterios de Aceptación", ""))
        features.append(create_feature_vector(StoryEstimationRequest(
            title=str(row.get("Titulo", "")),
            description=str(row.get("Historia de Usuario", "")),
            acceptance_criteria=[line.strip() for line in criteria.splitlines() if line.strip()],
        ))[0])
    targets = {
        "point": df["Custom field (Story Points)"].to_numpy(dtype=np.float32),
        "time": df["Duracion_Sprint"].to_numpy(dtype=np.float32),
        "cost": df["Costo_por_dia"].to_numpy(dtype=np.float32),
        "effort": df["Esfuerzo_por_Puntos_Historia"].to_numpy(dtype=np.float32),
    }
    models = EstimationModels(str(MODEL_DIR))
    models.train(np.asarray(features, dtype=np.float32), targets)
    models.features_columns = [f"linguistic_feature_{index}" for index in range(10)]
    models.save(str(MODEL_FILE))
    return models


# ============================================================================
# RAG, multiagente, roles, dashboard y exportación T-Shirt
# ============================================================================

async def _ml_predictor(epic: Dict[str, object]) -> Dict[str, object]:
    criteria = str(epic.get("acceptance_criteria", ""))
    response = await estimate_single_story(StoryEstimationRequest(
        title=str(epic.get("name", "Épica")),
        description=str(epic.get("description", "")),
        acceptance_criteria=[line.strip() for line in criteria.splitlines() if line.strip()],
    ))
    return response.model_dump()


def _agents() -> MultiAgentEstimator:
    predictor = _ml_predictor if estimation_models and estimation_models.rf_models else None
    return MultiAgentEstimator(knowledge_base, predictor)


@app.post("/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    """Carga el template Excel y reconstruye el índice RAG y catálogo de roles."""
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="El archivo debe ser .xlsx")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp:
        temp.write(await file.read())
        temp_path = Path(temp.name)
    try:
        return {"status": "success", **knowledge_base.ingest(temp_path)}
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"No fue posible indexar el Excel: {exc}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


@app.get("/knowledge/status")
async def knowledge_status():
    return {
        "loaded": bool(knowledge_base.chunks or knowledge_base.load()),
        "chunks": len(knowledge_base.chunks),
        "template": knowledge_base.workbook_path.exists(),
    }


@app.get("/knowledge/search")
async def search_knowledge(q: str, limit: int = 6):
    return {"query": q, "results": knowledge_base.search(q, limit)}


@app.get("/roles")
async def list_roles():
    return {"roles": knowledge_base.get_roles()}


@app.post("/roles")
async def create_role(role: RoleRequest):
    roles = knowledge_base.get_roles()
    if any(item["name"].casefold() == role.name.casefold() for item in roles):
        raise HTTPException(status_code=409, detail="El rol ya existe")
    roles.append(role.model_dump())
    return {"roles": knowledge_base.save_roles(roles)}


@app.put("/roles/{role_name}")
async def update_role(role_name: str, role: RoleRequest):
    roles = knowledge_base.get_roles()
    index = next((i for i, item in enumerate(roles) if item["name"].casefold() == role_name.casefold()), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    updated = role.model_dump()
    if not updated["source_row"]:
        updated["source_row"] = roles[index].get("source_row", 0)
    roles[index] = updated
    return {"roles": knowledge_base.save_roles(roles)}


@app.post("/agent/chat")
async def agent_chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Escribe una pregunta")
    return await _agents().chat(request.message)


@app.post("/project/analyze")
async def analyze_project():
    global latest_analysis
    if not knowledge_base.workbook_path.exists():
        raise HTTPException(status_code=409, detail="Primero carga el template Excel")
    latest_analysis = await _agents().analyze_project()
    return latest_analysis


@app.get("/dashboard")
async def get_dashboard():
    if latest_analysis is None:
        raise HTTPException(status_code=404, detail="Ejecuta POST /project/analyze primero")
    return latest_analysis


@app.post("/export/excel")
async def export_excel():
    if latest_analysis is None:
        raise HTTPException(status_code=409, detail="Ejecuta el análisis antes de exportar")
    output = EXPORT_DIR / f"estimacion_completa_{uuid.uuid4().hex[:8]}.xlsx"
    knowledge_base.export(output, latest_analysis)
    return FileResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=output.name,
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )
