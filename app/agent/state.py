from typing import Any, TypedDict

from app.models.schemas import LeadAssessment


class AgentState(TypedDict, total=False):
    lead_id: str
    message: str
    history: list[dict[str, str]]
    lead: dict[str, Any] | None
    assessment: LeadAssessment
    action_result: Any
    tool_calls: list[str]
    response: str
