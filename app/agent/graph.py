import asyncio
import os
import re
import sys
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.agent.prompts import ASSESSMENT_SYSTEM, REPLY_SYSTEM
from app.agent.state import AgentState
from app.db.database import get_history, get_lead, save_message, update_lead
from app.models.schemas import LeadAssessment
from dotenv import load_dotenv

load_dotenv()


def _llm():
    if not os.getenv("GROQ_API_KEY"):
        return None

    from langchain_groq import ChatGroq

    return ChatGroq(
        model=os.getenv("GROQ_MODEL"),
        temperature=0
    )


async def call_mcp_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Start the local MCP server over stdio and call one typed tool."""
    server_file = Path(__file__).resolve().parents[1] / "mcp" / "server.py"
    project_root = str(Path(__file__).resolve().parents[2])
    params = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp.server"], env=os.environ.copy(), cwd=project_root)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            if result.isError:
                raise RuntimeError(f"MCP tool {name} failed: {result.content}")
            parsed = []
            for item in result.content:
                if getattr(item, "text", None):
                    try:
                        import json
                        parsed.append(json.loads(item.text))
                    except ValueError:
                        parsed.append(item.text)
            return parsed[0] if len(parsed) == 1 else parsed


def _fallback_assessment(message: str, lead: dict | None) -> LeadAssessment:
    text = message.lower()
    assessment = LeadAssessment()
    match = re.search(r"\b(\d{1,6})\s*(?:-\s*)?(?:person|people|employee|employees|seat|seats|user|users)\b", text)
    size = int(match.group(1)) if match else (lead or {}).get("company_size")
    requirement = None
    for keyword in ("crm", "sales follow-up", "follow-up", "automation", "customer management"):
        if keyword in text:
            requirement = keyword
            break
    current = None
    if "excel" in text or "spreadsheet" in text:
        current = "Excel/spreadsheets"
    if any(word in text for word in ("buy", "looking for", "need", "want", "interested")):
        assessment.intent = "buy"
    if any(word in text for word in ("tomorrow", "next week", "call me", "contact me", "follow up", "follow-up")) and any(word in text for word in ("contact", "call", "follow", "tomorrow", "next week")):
        assessment.next_action = "create_followup"
    elif any(word in text for word in ("technical architecture", "custom integration", "security audit", "speak to a person", "human", "representative")):
        assessment.next_action = "handoff"
    elif requirement:
        assessment.next_action = "search_products"
    assessment.company_size = size
    assessment.requirements = requirement or (lead or {}).get("requirements")
    assessment.current_solution = current or (lead or {}).get("current_solution")
    if assessment.intent == "buy" and (size or assessment.requirements):
        assessment.lead_status = "qualified"
        assessment.qualification_reason = "Active business need identified; team or requirement is known."
        assessment.confidence = 0.72
    elif assessment.intent == "buy":
        assessment.lead_status = "qualifying"
        assessment.confidence = 0.52
    if assessment.next_action == "handoff":
        assessment.lead_status = "handoff"
        assessment.qualification_reason = "The request needs a human specialist."
        assessment.confidence = 0.85
    return assessment


async def analyze(state: AgentState) -> dict:
    lead = state.get("lead")
    model = _llm()
    if model:
        try:
            structured = model.with_structured_output(LeadAssessment)
            context = f"Existing lead: {lead}\nConversation: {state.get('history', [])}\nLatest customer message: {state['message']}"
            assessment = await structured.ainvoke([SystemMessage(content=ASSESSMENT_SYSTEM), HumanMessage(content=context)])
        except Exception:
            assessment = _fallback_assessment(state["message"], lead)
    else:
        assessment = _fallback_assessment(state["message"], lead)
    return {"assessment": assessment, "tool_calls": []}


def route(state: AgentState) -> str:
    return state["assessment"].next_action


async def run_action(state: AgentState) -> dict:
    assessment = state["assessment"]
    lead_id, message = state["lead_id"], state["message"]
    fields = {"company_size": assessment.company_size, "requirements": assessment.requirements,
              "current_solution": assessment.current_solution, "lead_status": assessment.lead_status,
              "qualification_reason": assessment.qualification_reason}
    await call_mcp_tool("update_lead", {"lead_id": lead_id, "fields": fields})
    action = assessment.next_action
    if action == "search_products":
        result = await call_mcp_tool("search_products", {"query": assessment.requirements or message})
        tool = "search_products"
    elif action == "create_followup":
        when = "tomorrow" if "tomorrow" in message.lower() else "requested time (please confirm exact time)"
        result = await call_mcp_tool("create_followup", {"lead_id": lead_id, "scheduled_for": when, "note": message})
        tool = "create_followup"
    elif action == "handoff":
        reason = assessment.qualification_reason or "Customer request needs a human specialist."
        result = await call_mcp_tool("handoff_to_human", {"lead_id": lead_id, "reason": reason})
        tool = "handoff_to_human"
    else:
        result, tool = None, ""
    return {"action_result": result, "tool_calls": ["update_lead"] + ([tool] if tool else [])}


async def respond(state: AgentState) -> dict:
    assessment, result = state["assessment"], state.get("action_result")
    model = _llm()
    if model:
        try:
            prompt = f"Customer message: {state['message']}\nAssessment: {assessment.model_dump()}\nAction result: {result}\nReply naturally. Ask one useful question if more qualification is needed."
            response = (await model.ainvoke([SystemMessage(content=REPLY_SYSTEM), HumanMessage(content=prompt)])).content
            if isinstance(response, list):
                response = " ".join(str(part.get("text", "")) for part in response if isinstance(part, dict))
            response = str(response)
        except Exception:
            response = ""
    else:
        response = ""
    if not response:
        if assessment.next_action == "search_products":
            names = ", ".join(item.get("name", "") for item in (result if isinstance(result, list) else []) if isinstance(item, dict))
            response = f"Based on your needs, these options may fit: {names}. How many people would need access?" if names else "I can help find a suitable option. How many people would need access?"
        elif assessment.next_action == "create_followup":
            response = "I’ve recorded a follow-up request for tomorrow. What time and contact method work best?" if "tomorrow" in state["message"].lower() else "I’ve recorded your follow-up request. What date and time work best?"
        elif assessment.next_action == "handoff":
            response = "I’ve asked a human specialist to follow up and help with this request."
        elif assessment.lead_status == "qualified":
            response = "Thanks, I understand the need. What is your current solution, and when are you hoping to make a change?"
        else:
            response = "I can help with that. Could you share your team size and the main outcome you want from a CRM?"
    await asyncio.to_thread(save_message, state["lead_id"], "assistant", response)
    return {"response": response}


builder = StateGraph(AgentState)
builder.add_node("analyze", analyze)
builder.add_node("act", run_action)
builder.add_node("respond", respond)
builder.add_edge(START, "analyze")
builder.add_edge("analyze", "act")
builder.add_edge("act", "respond")
builder.add_edge("respond", END)
graph = builder.compile()


async def chat(lead_id: str, message: str, contact: dict | None = None) -> dict:
    if not get_lead(lead_id):
        await asyncio.to_thread(update_lead, lead_id, **(contact or {}))
    elif contact:
        await asyncio.to_thread(update_lead, lead_id, **contact)
    await asyncio.to_thread(save_message, lead_id, "user", message)
    history = await asyncio.to_thread(get_history, lead_id)
    lead = get_lead(lead_id)
    result = await graph.ainvoke({"lead_id": lead_id, "message": message, "history": history,
                                  "lead": lead.model_dump(mode="json") if lead else None})
    return {"lead_id": lead_id, "response": result["response"], "assessment": result["assessment"], "tool_calls": result.get("tool_calls", [])}
