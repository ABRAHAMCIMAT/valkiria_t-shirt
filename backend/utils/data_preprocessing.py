"""
Data preprocessing and feature engineering for epic estimation.
Handles JIRA data cleaning, feature creation, and encoding.
"""

import re
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class JiraDataPreprocessor:
    """Preprocesses JIRA data for model training and prediction."""

    def __init__(self):
        self.processed_df = None
        self.missing_report = {}

    def load_and_clean(self, csv_path: str, missing_threshold: float = 0.55) -> pd.DataFrame:
        """
        Load JIRA CSV and perform initial cleaning.

        Args:
            csv_path: Path to JIRA CSV export
            missing_threshold: Drop columns with >this proportion missing values

        Returns:
            Cleaned DataFrame
        """
        print(f"Loading data from {csv_path}...")
        df = pd.read_csv(csv_path, encoding='utf-8')
        print(f"Loaded {len(df)} rows and {len(df.columns)} columns")

        # Strip whitespace from column names
        df.columns = df.columns.str.strip()

        # Report missing values
        self._report_missing_values(df)

        # Drop columns with too many missing values
        missing_percentage = df.isnull().mean() * 100
        columns_to_keep = missing_percentage[missing_percentage < missing_threshold].index.tolist()

        print(f"\nDropping {len(df.columns) - len(columns_to_keep)} columns with >{missing_threshold}% missing")
        df = df[columns_to_keep]

        self.processed_df = df
        return df

    def _report_missing_values(self, df: pd.DataFrame):
        """Report missing values by column."""
        total = len(df)
        missing_cols = [col for col in df.columns if df[col].isnull().sum() > 0]

        if missing_cols:
            print("\nMissing values report:")
            for col in missing_cols:
                null_count = df[col].isnull().sum()
                percent = (null_count / total) * 100
                print(f"  {col}: {null_count} ({percent:.2f}%)")
                self.missing_report[col] = percent

    def select_columns(self) -> pd.DataFrame:
        """Select relevant columns for modeling."""
        if self.processed_df is None:
            raise ValueError("No data loaded. Call load_and_clean first.")

        desired_columns = [
            'Summary', 'Issue key', 'Issue id', 'Issue Type', 'Status',
            'Project key', 'Project name', 'Project type', 'Project lead',
            'Project lead id', 'Description', 'Priority', 'Resolution',
            'Assignee', 'Reporter', 'Sprint', 'Status Category',
            'Status Category Changed',
            'Custom field (Story Points)',
            'Custom field (Criterios de aceptación)',
            'Custom field (Reglas de Negocio)',
            'Custom field (Solución Técnica)',
            'Created'
        ]

        # Keep only columns that exist in data
        existing_cols = [col for col in desired_columns if col in self.processed_df.columns]
        df_selected = self.processed_df[existing_cols]

        print(f"Selected {len(existing_cols)} columns for analysis")
        return df_selected

    def impute_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """Impute missing values using median/mode strategy."""
        df = df.copy()

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object']).columns.tolist()

        # Numeric imputation with median
        for col in numeric_cols:
            if df[col].isnull().any():
                median_val = df[col].median()
                df[col] = df[col].fillna(median_val)
                print(f"  Imputed {col} with median: {median_val}")

        # Categorical imputation with mode
        for col in categorical_cols:
            if df[col].isnull().any():
                mode_val = df[col].mode()[0] if not df[col].mode().empty else "Unknown"
                df[col] = df[col].fillna(mode_val)
                print(f"  Imputed {col} with mode: {mode_val}")

        return df

    def extract_sprint_dates(self, sprint_str: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract start and end dates from Sprint string.

        Examples:
            "Sprint 1, 01-ene a 31-ene" -> ("2025-01-01", "2025-01-31")
            "Sprint 26 | Q2 01 Nov a 22 Nov" -> ("2025-11-01", "2025-11-22")  (JIRA export)
        """
        if pd.isna(sprint_str):
            return None, None

        # Match date patterns like "01-ene a 31-ene" or "01 Nov a 22 Nov"
        pattern = r'(\d{1,2})[-\s]([a-záéíóú]+)\s+a\s+(\d{1,2})[-\s]([a-záéíóú]+)'
        match = re.search(pattern, str(sprint_str), re.IGNORECASE)

        if not match:
            return None, None

        day_start, month_start, day_end, month_end = match.groups()

        month_map = {
            'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
        }

        month_start_num = month_map.get(month_start.lower()[:3], '01')
        month_end_num = month_map.get(month_end.lower()[:3], '12')

        # Assume current year (2025 based on notebook)
        year = '2025'
        start_date = f"{year}-{month_start_num}-{day_start.zfill(2)}"
        end_date = f"{year}-{month_end_num}-{day_end.zfill(2)}"

        return start_date, end_date

    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create temporal features from Sprint and Created dates."""
        df = df.copy()

        # Extract sprint dates
        df[['sprint_start', 'sprint_end']] = df['Sprint'].apply(
            lambda x: pd.Series(self.extract_sprint_dates(x))
        )

        # Calculate sprint duration
        def calc_sprint_duration(start, end):
            if pd.isna(start) or pd.isna(end):
                return np.nan
            try:
                delta = pd.to_datetime(end) - pd.to_datetime(start)
                # Sprints that cross the year ("15 Dic a 05 Ene") share the assumed year
                return delta.days if delta.days >= 0 else delta.days + 365
            except Exception:
                return np.nan

        df['Duracion_Sprint'] = df.apply(
            lambda row: calc_sprint_duration(row['sprint_start'], row['sprint_end']),
            axis=1
        )

        print("Created time features: Duracion_Sprint")
        return df

    def create_cost_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create cost-related features."""
        df = df.copy()

        # Generate random hourly wages by assignee for demo
        np.random.seed(42)
        unique_assignees = df['Assignee'].dropna().unique()
        assignee_wages = {
            assignee: np.random.randint(200, 401)
            for assignee in unique_assignees
        }

        df['hourly_wage'] = df['Assignee'].map(assignee_wages).fillna(250)
        df['Costo_por_dia'] = df['hourly_wage'] * 8  # 8-hour workday

        print("Created cost features: hourly_wage, Costo_por_dia")
        return df

    def create_effort_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create effort-related features."""
        df = df.copy()

        # Effort per story point (estimated as cost per point)
        story_points = pd.to_numeric(df.get('Custom field (Story Points)', 0), errors='coerce').fillna(1)
        cost_per_day = df.get('Costo_por_dia', 250)

        df['Esfuerzo_por_Puntos_Historia'] = cost_per_day / (story_points + 1)

        print("Created effort features: Esfuerzo_por_Puntos_Historia")
        return df

    def fix_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fix data outliers and invalid values."""
        df = df.copy()

        # Fix story points > 13 (outliers)
        if 'Custom field (Story Points)' in df.columns:
            invalid_mask = df['Custom field (Story Points)'] > 13
            if invalid_mask.any():
                median_val = df[~invalid_mask]['Custom field (Story Points)'].median()
                df.loc[invalid_mask, 'Custom field (Story Points)'] = np.nan
                df['Custom field (Story Points)'] = df['Custom field (Story Points)'].fillna(median_val)
                print(f"Fixed {invalid_mask.sum()} story points > 13")

        # Fix negative Duracion_Sprint
        if 'Duracion_Sprint' in df.columns:
            invalid_mask = df['Duracion_Sprint'] < 0
            if invalid_mask.any():
                median_val = df[df['Duracion_Sprint'] >= 0]['Duracion_Sprint'].median()
                df.loc[invalid_mask, 'Duracion_Sprint'] = np.nan
                df['Duracion_Sprint'] = df['Duracion_Sprint'].fillna(median_val)
                print(f"Fixed {invalid_mask.sum()} negative sprint durations")

        return df

    def encode_categorical(self, df: pd.DataFrame, categorical_cols: List[str] = None) -> Tuple[pd.DataFrame, Dict]:
        """
        Encode categorical variables.

        Returns:
            Tuple of (encoded_df, encoding_dict)
        """
        if categorical_cols is None:
            categorical_cols = [
                'Issue Type', 'Status', 'Priority', 'Resolution',
                'Status Category', 'Project type'
            ]

        df = df.copy()
        encoding_dict = {}

        for col in categorical_cols:
            if col in df.columns:
                unique_vals = df[col].dropna().unique()
                encoding = {val: idx for idx, val in enumerate(unique_vals)}
                encoding_dict[col] = encoding

                df[f'{col}_encoded'] = df[col].map(encoding).fillna(-1).astype(int)
                print(f"Encoded {col}: {len(encoding)} categories")

        return df, encoding_dict

    def prepare_for_modeling(self, csv_path: str) -> Tuple[pd.DataFrame, Dict]:
        """
        Full preprocessing pipeline.

        Returns:
            Tuple of (processed_df, metadata_dict)
        """
        print("="*60)
        print("JIRA DATA PREPROCESSING PIPELINE")
        print("="*60)

        # Step 1: Load and clean
        df = self.load_and_clean(csv_path)

        # Step 2: Select columns
        df = self.select_columns()

        # Step 3: Impute missing values
        print("\nImputing missing values...")
        df = self.impute_missing_values(df)

        # Step 4: Create features
        print("\nCreating temporal features...")
        df = self.create_time_features(df)

        print("Creating cost features...")
        df = self.create_cost_features(df)

        print("Creating effort features...")
        df = self.create_effort_features(df)

        # Step 5: Fix outliers
        print("\nFixing outliers...")
        df = self.fix_outliers(df)

        # Step 6: Encode categorical variables
        print("\nEncoding categorical variables...")
        df, encoding_dict = self.encode_categorical(df)

        metadata = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'encoding_dict': encoding_dict,
            'missing_report': self.missing_report
        }

        print("\n" + "="*60)
        print(f"Preprocessing complete: {len(df)} rows × {len(df.columns)} columns")
        print("="*60)

        return df, metadata

    @staticmethod
    def is_jira_export(df: pd.DataFrame) -> bool:
        """A raw JIRA export has 'Summary' instead of the training 'Titulo' column."""
        return 'Summary' in df.columns and 'Titulo' not in df.columns

    def to_training_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert a raw JIRA export into the training schema used by POST /train:
        Titulo, Historia de Usuario, Criterios de Aceptación and the four targets.
        """
        df = df.copy()
        df.columns = df.columns.str.strip()
        df['Custom field (Story Points)'] = pd.to_numeric(df['Custom field (Story Points)'], errors='coerce')
        df = df.dropna(subset=['Custom field (Story Points)'])

        if 'Sprint' not in df.columns:
            df['Sprint'] = np.nan
        df = self.create_time_features(df)
        median_days = df['Duracion_Sprint'].median()
        # Two-week sprints when the export has no parseable sprint dates
        df['Duracion_Sprint'] = df['Duracion_Sprint'].fillna(14 if pd.isna(median_days) else median_days)

        if 'Assignee' not in df.columns:
            df['Assignee'] = np.nan
        df = self.create_cost_features(df)
        df = self.create_effort_features(df)
        df = self.fix_outliers(df)

        criteria = df.get('Custom field (Criterios de aceptación)', pd.Series('', index=df.index))
        description = df.get('Description', pd.Series('', index=df.index))
        return pd.DataFrame({
            'Titulo': df['Summary'].fillna(''),
            'Historia de Usuario': description.fillna(''),
            'Criterios de Aceptación': criteria.fillna(''),
            'Custom field (Story Points)': df['Custom field (Story Points)'],
            'Duracion_Sprint': df['Duracion_Sprint'],
            'Costo_por_dia': df['Costo_por_dia'],
            'Esfuerzo_por_Puntos_Historia': df['Esfuerzo_por_Puntos_Historia'],
        }).reset_index(drop=True)


def process_user_excel(excel_path: str, preprocessor: JiraDataPreprocessor = None) -> pd.DataFrame:
    """
    Process user-uploaded Excel file for prediction.

    Expected columns: Titulo, Historia de Usuario, Criterios de Aceptación
    """
    df = pd.read_excel(excel_path)

    # Strip whitespace from column names
    df.columns = df.columns.str.strip()

    # Check for required columns (case-insensitive)
    required_cols = ['Titulo', 'Historia de Usuario', 'Criterios de Aceptación']
    df_cols_lower = {col.lower(): col for col in df.columns}

    missing = []
    for req_col in required_cols:
        if req_col.lower() not in df_cols_lower:
            missing.append(req_col)

    if missing:
        # Try to work with what we have
        print(f"Warning: Excel missing some columns: {missing}")
        print(f"Found columns: {list(df.columns)}")

    return df
