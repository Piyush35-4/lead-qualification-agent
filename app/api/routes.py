from fastapi import APIRouter, HTTPException

from app.agent.graph import chat
from app.db.database import get_lead, init_db
from app.models.schemas import ChatRequest, ChatResponse, Lead

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    init_db()
    try:
        result = await chat(request.lead_id, request.message,
                            {"name": request.name, "email": str(request.email) if request.email else None, "company": request.company})
        return ChatResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent failed: {exc}") from exc


@router.get("/leads/{lead_id}", response_model=Lead)
def lead_endpoint(lead_id: str) -> Lead:
    init_db()
    lead = get_lead(lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead
