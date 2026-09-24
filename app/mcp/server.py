"""FastMCP tool server. Run with: python -m app.mcp.server"""
from mcp.server.fastmcp import FastMCP

from app.db.database import create_followup as db_create_followup, create_handoff, get_lead as db_get_lead, update_lead as db_update_lead

mcp = FastMCP("lead-crm")


@mcp.tool()
def search_products(query: str) -> list[dict[str, str]]:
    """Find mock products relevant to a customer's stated need."""
    catalog = [
        {"name": "Starter CRM", "description": "Contact management and simple sales pipeline for small teams."},
        {"name": "Growth CRM", "description": "CRM with automated sales follow-ups, reporting, and team workflows."},
        {"name": "Enterprise CRM", "description": "Advanced permissions, integrations, and dedicated onboarding."},
    ]
    terms = set(query.lower().split())
    return sorted(catalog, key=lambda p: sum(t in (p["name"] + " " + p["description"]).lower() for t in terms), reverse=True)[:2]


@mcp.tool()
def get_lead(lead_id: str) -> dict | None:
    """Look up a lead by its ID in the mock CRM."""
    lead = db_get_lead(lead_id)
    return lead.model_dump(mode="json") if lead else None


@mcp.tool()
def update_lead(lead_id: str, fields: dict) -> dict:
    """Create or update CRM fields for a lead. Only provided non-empty fields are changed."""
    return db_update_lead(lead_id, **fields).model_dump(mode="json")


@mcp.tool()
def create_followup(lead_id: str, scheduled_for: str, note: str) -> dict:
    """Create a mock CRM follow-up with a date/time string and note."""
    return db_create_followup(lead_id, scheduled_for, note)


@mcp.tool()
def handoff_to_human(lead_id: str, reason: str) -> dict:
    """Record a request for a human sales representative to take over."""
    return create_handoff(lead_id, reason)


if __name__ == "__main__":
    mcp.run(transport="stdio")
