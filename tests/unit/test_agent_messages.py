import json
from src.agents.shared.messages import AgentMessage, CohortSpec


def test_agent_message_schema_roundtrip():
    spec = CohortSpec(condition_snomed=["44054006"], min_age=50, max_age=85)
    msg = AgentMessage(simulation_id="abc", role="cohort", payload=spec.model_dump())
    data = json.loads(msg.model_dump_json())
    assert data["role"] == "cohort"
