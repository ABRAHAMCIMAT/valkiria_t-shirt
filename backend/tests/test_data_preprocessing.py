"""Tests unitarios de utils/data_preprocessing.py (funciones puras, sin modelos)."""
import pandas as pd

from utils.data_preprocessing import JiraDataPreprocessor


class TestExtractSprintDates:
    """extract_sprint_dates parsea el formato de Sprint usado en los exports de JIRA."""

    def setup_method(self):
        self.preprocessor = JiraDataPreprocessor()

    def test_parses_valid_sprint_string(self):
        start, end = self.preprocessor.extract_sprint_dates("Sprint 1, 01-ene a 31-ene")

        assert start == "2025-01-01"
        assert end == "2025-01-31"

    def test_handles_different_months(self):
        start, end = self.preprocessor.extract_sprint_dates("Sprint 7, 05-ago a 18-sep")

        assert start == "2025-08-05"
        assert end == "2025-09-18"

    def test_returns_none_for_missing_value(self):
        start, end = self.preprocessor.extract_sprint_dates(pd.NA)

        assert start is None
        assert end is None

    def test_returns_none_for_unparseable_string(self):
        start, end = self.preprocessor.extract_sprint_dates("texto sin fechas")

        assert start is None
        assert end is None

    def test_is_case_insensitive_on_month_abbreviation(self):
        start, end = self.preprocessor.extract_sprint_dates("Sprint 2, 10-ENE a 20-FEB")

        assert start == "2025-01-10"
        assert end == "2025-02-20"

    def test_parses_jira_export_sprint_format(self):
        start, end = self.preprocessor.extract_sprint_dates("Sprint 26 | Q2 01 Nov a 22 Nov")

        assert start == "2025-11-01"
        assert end == "2025-11-22"


class TestJiraExportToTrainingFrame:
    """to_training_frame convierte el export crudo de JIRA al esquema de POST /train."""

    def _export(self):
        return pd.DataFrame({
            "Summary": ["Login", "Reporte", "Sin puntos"],
            "Description": ["Como usuario quiero entrar", None, "x"],
            "Custom field (Criterios de aceptación)": ["Valida password", "Exporta CSV", None],
            "Custom field (Story Points)": ["3", 5, None],
            "Sprint": ["Sprint 1 | Q1 01 Nov a 22 Nov", "texto sin fechas", None],
            "Assignee": ["Ana", None, "Luis"],
        })

    def test_detects_raw_jira_export(self):
        assert JiraDataPreprocessor.is_jira_export(self._export())
        assert not JiraDataPreprocessor.is_jira_export(pd.DataFrame({"Titulo": [], "Summary": []}))

    def test_builds_training_columns_with_numeric_targets(self):
        frame = JiraDataPreprocessor().to_training_frame(self._export())

        assert list(frame.columns) == [
            "Titulo", "Historia de Usuario", "Criterios de Aceptación", "Custom field (Story Points)",
            "Duracion_Sprint", "Costo_por_dia", "Esfuerzo_por_Puntos_Historia",
        ]
        assert frame["Titulo"].tolist() == ["Login", "Reporte"]
        assert frame["Historia de Usuario"].tolist() == ["Como usuario quiero entrar", ""]
        assert frame["Custom field (Story Points)"].tolist() == [3, 5]
        # El sprint sin fechas toma la mediana de los que sí se pudieron leer
        assert frame["Duracion_Sprint"].tolist() == [21, 21]
        assert frame.drop(columns=["Titulo", "Historia de Usuario", "Criterios de Aceptación"]).notna().all().all()
