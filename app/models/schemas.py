from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


LeadStatus = Literal["new", "qualifying", "qualified", "unqualified", "handoff"]


class Lead(BaseModel):
    lead_id: str
    name: str | None = None
    email: str | None = None
    company: str | None = None
    company_size: int | None = None
    requirements: str | None = None
    current_solution: str | None = None
    lead_status: LeadStatus = "new"
    qualification_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadAssessment(BaseModel):
    lead_status: LeadStatus = "qualifying"
    intent: Literal["buy", "research", "support", "unknown"] = "unknown"
    company_size: int | None = Field(default=None, ge=1)
    requirements: str | None = None
    current_solution: str | None = None
    next_action: Literal["ask_question", "search_products", "create_followup", "handoff", "none"] = "ask_question"
    confidence: float = Field(default=0.3, ge=0, le=1)
    qualification_reason: str | None = None


class ChatRequest(BaseModel):
    lead_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=5000)
    name: str | None = None
    email: EmailStr | None = None
    company: str | None = None


class ChatResponse(BaseModel):
    lead_id: str
    response: str
    assessment: LeadAssessment
    tool_calls: list[str] = Field(default_factory=list)


class Followup(BaseModel):
    followup_id: int
    lead_id: str
    scheduled_for: str
    note: str
    status: str


class Handoff(BaseModel):
    handoff_id: int
    lead_id: str
    reason: str
    status: str
