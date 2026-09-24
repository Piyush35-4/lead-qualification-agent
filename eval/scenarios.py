"""Small deterministic scenarios; run with `python -m eval.scenarios`."""
import asyncio
import os

from app.agent.graph import chat
from app.db.database import init_db, list_records


SCENARIOS = [
    {"name": "product_search", "lead_id": "eval_product", "message": "We are a 20-person company looking for CRM software", "expected_tool": "search_products"},
    {"name": "follow_up", "lead_id": "eval_followup", "message": "Please contact me tomorrow", "expected_tool": "create_followup"},
    {"name": "human_handoff", "lead_id": "eval_handoff", "message": "I need to discuss a custom integration with a human representative", "expected_tool": "handoff_to_human"},
    {"name": "clarification", "lead_id": "eval_clarify", "message": "Maybe we need something for our business", "expected_tool": None},
]


async def run() -> None:
    results = []
    for scenario in SCENARIOS:
        result = await chat(scenario["lead_id"], scenario["message"])
        expected = scenario["expected_tool"]
        passed = expected in result["tool_calls"] if expected else result["tool_calls"] == ["update_lead"]
        if expected == "create_followup":
            passed = passed and bool(list_records("followups", scenario["lead_id"]))
        if expected == "handoff_to_human":
            passed = passed and bool(list_records("handoffs", scenario["lead_id"]))
        results.append((scenario["name"], passed, result["assessment"].lead_status))
    for name, passed, status in results:
        print(f"{'PASS' if passed else 'FAIL'} {name}: lead_status={status}")
    print(f"{sum(row[1] for row in results)}/{len(results)} scenarios passed")
    if not all(row[1] for row in results):
        raise SystemExit(1)


if __name__ == "__main__":
    os.environ["DATABASE_PATH"] = os.path.join(os.path.dirname(__file__), "..", "data", "evaluation.db")
    init_db()
    asyncio.run(run())
