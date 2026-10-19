from pathlib import Path

from openpyxl import load_workbook

from services.workbook_service import WorkbookKnowledgeBase

TEMPLATE = Path(__file__).parents[1] / "data" / "T-Shirt_template.xlsx"


def test_ingest_extracts_structured_knowledge(tmp_path):
    knowledge = WorkbookKnowledgeBase(tmp_path / "knowledge")
    result = knowledge.ingest(TEMPLATE)
    assert "Roles" in result["sheets"]
    assert result["chunks"] > 20
    assert result["roles"] > 0
    assert result["questionnaire_items"] > 0
    assert result["epics"] > 0
    assert knowledge.search("infraestructura monitoreo")


def test_export_fills_results_and_roles(tmp_path):
    knowledge = WorkbookKnowledgeBase(tmp_path / "knowledge")
    knowledge.ingest(TEMPLATE)
    output = tmp_path / "result.xlsx"
    knowledge.export(output, {
        "roles": [{"name": "PM", "area": "TI", "required": True, "collaborators": 1, "cost_hourly": 200}],
        "questionnaire": [{"row": 3, "answer": "Respuesta agente", "cost": 123}],
        "epics": [{"row": 3, "size": "L", "weeks": 4, "cost": 1000}],
        "summary": {"total_weeks": 4, "total_cost": 1123, "complexity": "L", "mvp_count": 1, "executive_summary": "Validado"},
    })
    workbook = load_workbook(output, data_only=False)
    assert workbook["Resultado"]["B6"].value == "4.0 Semanas"
    assert workbook["Resultado"]["B7"].value == 1123
    assert workbook["Cuestionario"]["H3"].value == "Respuesta agente"
    assert workbook["Epic Backlog"]["T3"].value == "L"
