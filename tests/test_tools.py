import asyncio

from app.agent.graph import call_mcp_tool


def test_mcp_product_search():
    result = asyncio.run(call_mcp_tool("search_products", {"query": "automated sales follow-ups"}))
    assert result
    assert "name" in result[0]


def test_mcp_followup_creation():
    result = asyncio.run(call_mcp_tool("create_followup", {"lead_id": "tool-test", "scheduled_for": "tomorrow", "note": "call"}))
    assert result["status"] == "scheduled"
