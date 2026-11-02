"""Cuestionario del orquestador con un LLM simulado (sin Ollama)."""
import asyncio
import json

from services.multi_agent import MultiAgentEstimator

QUESTION = {
    "number": 1,
    "row": 3,
    "topic": "Infraestructura",
    "question": "Define el tipo de infraestructura",
    "options": [
        {"row": 3, "answer": "Más de 10 componentes", "size": "XL", "annual_cost": 300},
        {"row": 4, "answer": "De 5 a 7 componentes", "size": "M", "annual_cost": 200},
        {"row": 5, "answer": "De 1 a 3 componentes", "size": "XS", "annual_cost": 100},
        {"row": 6, "answer": "NA", "size": "NA", "annual_cost": 0},
    ],
}
EPICS = [
    {"name": "Geo- Recaudo", "description": "Cobro en caja"},
    {"name": "EBS-Póliza contable", "description": "Genera póliza"},
    {"name": "Reportería diaria", "description": "Sin prefijo de plataforma"},
]


class FakeLLM:
    def __init__(self, size):
        self.size = size
        self.prompts = []
        self.schemas = []

    async def available(self):
        return True

    async def chat(self, system, prompt, temperature=0.2, json_mode=False, schema=None):
        self.prompts.append(prompt)
        self.schemas.append(schema)
        return json.dumps({"size": self.size, "reason": "Tres plataformas en el backlog"})

    @staticmethod
    def parse_json(content):
        return json.loads(content)


def _estimator(llm):
    estimator = MultiAgentEstimator(knowledge=None)
    estimator.llm = llm
    return estimator


def test_questionnaire_maps_chosen_size_to_its_option_row():
    llm = FakeLLM("M")

    [result] = asyncio.run(_estimator(llm)._analyze_questionnaire([QUESTION], EPICS, "M"))

    assert (result["option_row"], result["size"], result["cost"]) == (4, "M", 200)
    assert result["reason"] == "Tres plataformas en el backlog"


def test_options_are_offered_smallest_first_and_size_is_constrained():
    llm = FakeLLM("XS")

    asyncio.run(_estimator(llm)._analyze_questionnaire([QUESTION], EPICS, "M"))

    prompt = llm.prompts[0]
    assert prompt.index("NA: NA") < prompt.index("XS: ") < prompt.index("M: ") < prompt.index("XL: ")
    assert llm.schemas[0]["properties"]["size"]["enum"] == ["NA", "XS", "M", "XL"]
    assert "plataformas involucradas (2): EBS, Geo" in prompt


def test_unknown_size_falls_back_to_conservative_option():
    [result] = asyncio.run(_estimator(FakeLLM("XXL"))._analyze_questionnaire([QUESTION], EPICS, "M"))

    assert result["size"] == "M"
    assert result["reason"].startswith("Selección conservadora")
