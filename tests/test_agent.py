import asyncio

from app.agent.graph import chat
from app.db.database import list_records
from app.models.schemas import LeadAssessment


def test_structured_assessment_validation():
    assessment = LeadAssessment(lead_status="qualified", intent="buy", company_size=20, confidence=0.9)
    assert assessment.company_size == 20


def test_follow_up_scenario():
    result = asyncio.run(chat("lead-followup", "Please contact me tomorrow"))
    assert result["tool_calls"] == ["update_lead", "create_followup"]
    assert list_records("followups", "lead-followup")
