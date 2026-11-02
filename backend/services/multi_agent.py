"""Orquestación multiagente para estimaciones, cuestionario y revisión."""

from __future__ import annotations

import json
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

from services.llm_client import LLMClient
from services.workbook_service import WorkbookKnowledgeBase

SIZE_ORDER = ["XS", "S", "M", "L", "XL"]
OPTION_ORDER = ["NA", *SIZE_ORDER]
# Cabe con holgura en el contexto por defecto de Ollama (4096 tokens) junto con una pregunta
BACKLOG_CHARS = 8000
QUESTION_SYSTEM = (
    "Eres analista de arquitectura y costos. Lee el backlog y elige la talla de la opción que mejor "
    "corresponde a lo que el backlog describe. No elijas una talla mayor sin evidencia en el backlog: "
    "cuenta plataformas, integraciones y componentes mencionados. Si el backlog conecta varias "
    "plataformas, no elijas una opción que diga que no hay integración. Responde solo JSON."
)


class MultiAgentEstimator:
    """Especialistas independientes y un revisor que consolida resultados."""

    def __init__(
        self,
        knowledge: WorkbookKnowledgeBase,
        ml_predictor: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
    ):
        self.knowledge = knowledge
        self.llm = LLMClient()
        self.ml_predictor = ml_predictor

    async def chat(self, message: str) -> Dict[str, Any]:
        context = self.knowledge.search(message, 6)
        context_text = "\n".join(
            f"[{item['sheet']} fila {item['row']}] {item['text']}" for item in context
        )
        if not await self.llm.available():
            return {
                "answer": f"El modelo LLM no está disponible en {self.llm.base_url}. Inicia Ollama (`ollama serve`) y verifica que el modelo {self.llm.model} esté descargado.",
                "sources": context,
                "model": self.llm.model,
                "offline": True,
            }
        answer = await self.llm.chat(
            "Eres el agente coordinador de estimación de proyectos. Responde en español, cita hoja y fila, no inventes datos.",
            f"Pregunta: {message}\n\nContexto RAG:\n{context_text}",
        )
        return {"answer": answer, "sources": context, "model": self.llm.model, "offline": False}

    async def analyze_project(self) -> Dict[str, Any]:
        epics = self.knowledge.get_epics()
        roles = self.knowledge.get_roles()
        questionnaire = self.knowledge.get_questionnaire()

        epic_results = []
        for epic in epics:
            ml_result = await self._predict_epic(epic)
            epic_results.append({**epic, **ml_result})

        max_size = max((epic["size"] for epic in epic_results), key=SIZE_ORDER.index, default="XS")
        questionnaire_results = await self._analyze_questionnaire(questionnaire, epics, max_size)
        total_hours = sum(float(epic["effort_hours"]) for epic in epic_results)
        active_roles = [role for role in roles if role.get("required", True)]
        hourly_team_cost = sum(
            float(role.get("cost_hourly", 0)) * float(role.get("collaborators", 1))
            for role in active_roles
        )
        role_cost = total_hours * hourly_team_cost / max(len(active_roles), 1)
        epic_ml_cost = sum(float(epic.get("ml_cost", 0)) for epic in epic_results)
        questionnaire_cost = sum(float(item.get("cost", 0)) for item in questionnaire_results)
        total_cost = max(role_cost, epic_ml_cost) + questionnaire_cost
        total_weeks = sum(float(epic["weeks"]) for epic in epic_results)
        mvp_count = len({epic.get("mvp", "MVP1") for epic in epics}) or 1

        summary = {
            "total_weeks": round(total_weeks, 2),
            "total_cost": round(total_cost, 2),
            "complexity": max_size,
            "mvp_count": mvp_count,
            "epics": len(epic_results),
            "effort_hours": round(total_hours, 2),
            "executive_summary": (
                f"Estimación consolidada de {len(epic_results)} épicas en {mvp_count} MVP(s), "
                f"con complejidad máxima {max_size}. Validar supuestos y tarifas antes de aprobar."
            ),
        }
        result = {
            "summary": summary,
            "epics": epic_results,
            "questionnaire": questionnaire_results,
            "roles": roles,
            "additional_costs": self._additional_costs(questionnaire_results),
            "architecture": "Arquitectura contextual basada en las plataformas e integraciones descritas en el backlog; requiere validación del Arquitecto de Soluciones.",
            "process": "Flujo To-Be inferido de las épicas y criterios de aceptación; requiere validación del Product Owner.",
            "agents": ["estimador_ml", "analista_rag", "especialista_costos", "revisor"],
        }
        return await self._review(result)

    async def _predict_epic(self, epic: Dict[str, Any]) -> Dict[str, Any]:
        if self.ml_predictor:
            try:
                prediction = await self.ml_predictor(epic)
                points = max(1, float(prediction["point_estimate"]["ensemble"]))
                days = max(1, float(prediction["time_estimate"]["ensemble"]))
                effort = max(1, float(prediction["effort_estimate"]["ensemble"]))
                cost = max(0, float(prediction["cost_estimate"]["ensemble"]))
                return {
                    "story_points": round(points, 2),
                    "weeks": round(days / 5, 2),
                    "effort_hours": round(effort, 2),
                    "ml_cost": round(cost, 2),
                    "cost": round(cost, 2),
                    "size": self._size(points),
                    "estimation_source": "modelo_ensemble",
                }
            except Exception:
                pass
        text = f"{epic.get('description', '')} {epic.get('acceptance_criteria', '')}"
        criteria = max(1, len([line for line in text.splitlines() if line.strip()]))
        signals = sum(text.casefold().count(word) for word in ("integr", "api", "automat", "seguridad", "base de datos"))
        points = min(34, max(3, 3 + criteria + signals * 2))
        effort = points * 8
        return {
            "story_points": points,
            "weeks": round(effort / 40, 2),
            "effort_hours": effort,
            "ml_cost": 0,
            "cost": 0,
            "size": self._size(points),
            "estimation_source": "heurística_respaldo",
        }

    async def _analyze_questionnaire(self, questions, epics, complexity: str = "M") -> List[Dict[str, Any]]:
        if not questions or not await self.llm.available():
            return [self._question_result(question, None) for question in questions]
        platforms = self._platforms(epics)
        backlog = "\n".join(f"- {epic['name']}: {epic['description']}" for epic in epics)[:BACKLOG_CHARS]
        context = (
            f"Backlog del proyecto ({len(epics)} épicas, talla estimada por el modelo ML: {complexity}, "
            f"plataformas involucradas ({len(platforms)}): {', '.join(platforms) or 'no identificadas'}):\n{backlog}"
        )
        # Una pregunta por llamada: con todas juntas el modelo elegía la primera opción de cada una
        return [self._question_result(q, await self._answer_question(context, q)) for q in questions]

    async def _answer_question(self, context: str, question: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # El template lista XL primero y el modelo tiende a quedarse con la primera opción,
        # así que se presentan de menor a mayor
        options = sorted(
            question.get("options", []),
            key=lambda option: OPTION_ORDER.index(option["size"]) if option.get("size") in OPTION_ORDER else len(OPTION_ORDER),
        )
        sizes = list(dict.fromkeys(option.get("size", "NA") for option in options))
        if not sizes:
            return None
        listed = "\n".join(f"{option.get('size', 'NA')}: {option.get('answer', '')}" for option in options)
        prompt = (
            f"{context}\n\nTema: {question.get('topic', '')}\nPregunta: {question.get('question', '')}\n"
            f'Opciones:\n{listed}\n\nDevuelve {{"size": talla, "reason": "evidencia del backlog en una frase"}}.'
        )
        schema = {
            "type": "object",
            "properties": {"size": {"type": "string", "enum": sizes}, "reason": {"type": "string"}},
            "required": ["size", "reason"],
        }
        try:
            answer = self.llm.parse_json(await self.llm.chat(QUESTION_SYSTEM, prompt, temperature=0, schema=schema))
        except Exception:
            return None
        option = next((option for option in options if option.get("size") == answer.get("size")), None)
        return {"row": option["row"], "reason": answer.get("reason", "")} if option else None

    @staticmethod
    def _platforms(epics: List[Dict[str, Any]]) -> List[str]:
        """Plataformas tomadas del prefijo de las épicas ("EBS-Generación de póliza" -> EBS)."""
        prefixes = (re.match(r"\s*([^\s:-]{2,15})\s*-", str(epic.get("name", ""))) for epic in epics)
        return sorted({match.group(1) for match in prefixes if match})

    def _question_result(self, question, selected) -> Dict[str, Any]:
        options = question.get("options", [])
        option = None
        if selected:
            option = next((item for item in options if item["row"] == selected.get("row")), None)
        if option is None:
            option = next((item for item in options if item.get("size") == "M"), None)
            option = option or next((item for item in options if item.get("size") != "NA"), options[0] if options else {})
        return {
            "number": question.get("number"),
            "topic": question.get("topic"),
            "question": question.get("question"),
            "row": question.get("row", 0),
            "option_row": option.get("row", 0),
            "answer": option.get("answer", "NA"),
            "size": option.get("size", "NA"),
            "cost": option.get("annual_cost", 0),
            "reason": (selected or {}).get("reason", "Selección conservadora de respaldo; revisar con el especialista."),
        }

    async def _review(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """El revisor nunca altera números sin evidencia; añade observaciones."""
        result["review"] = {
            "status": "requires_human_validation",
            "warnings": [
                "Los costos del template se interpretan como mensuales y se convierten con 160 horas/mes.",
                "Las respuestas automáticas del cuestionario deben validarse antes de presupuesto final.",
            ],
        }
        if await self.llm.available():
            try:
                text = await self.llm.chat(
                    "Eres revisor senior de estimaciones. Señala máximo 5 riesgos, sin cambiar cifras. Responde en español.",
                    json.dumps({"summary": result["summary"], "epics": result["epics"]}, ensure_ascii=False),
                )
                result["review"]["llama_review"] = text
            except Exception:
                pass
        return result

    @staticmethod
    def _size(points: float) -> str:
        if points <= 3:
            return "XS"
        if points <= 5:
            return "S"
        if points <= 8:
            return "M"
        if points <= 13:
            return "L"
        return "XL"

    @staticmethod
    def _additional_costs(questionnaire: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        categories = {
            "Infraestructura": 0,
            "Servicios con Terceros": 0,
            "Licenciamiento": 0,
            "Soporte": 0,
        }
        for item in questionnaire:
            topic = str(item.get("topic", "")).casefold()
            category = "Infraestructura"
            if "licenc" in topic or "base de datos" in topic or "monitoreo" in topic:
                category = "Licenciamiento"
            elif "soporte" in topic:
                category = "Soporte"
            elif "tercer" in topic or "proveedor" in topic:
                category = "Servicios con Terceros"
            categories[category] += float(item.get("cost", 0))
        return [
            {"concept": name, "amount_mxn": round(value, 2), "amount_usd": round(value / 20, 2), "description": "Calculado desde Cuestionario"}
            for name, value in categories.items()
        ]
