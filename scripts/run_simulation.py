import json
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from src.agents.cohort.agent import CohortAgent
from src.agents.shared.messages import CohortSpec
from src.security.audit_ledger.ledger import AuditLedger, AuditEvent

# This CLI simulates the vertical slice using stubbed data

def main() -> None:
    simulation_id = str(uuid4())
    ledger = AuditLedger()
    ledger.write(AuditEvent(simulation_id=simulation_id, actor="cli", action="start"))

    # Load a tiny synthetic cohort spec fixture
    spec_path = Path("tests/fixtures/sample_protocol.json")
    if spec_path.exists():
        payload: Dict[str, Any] = json.loads(spec_path.read_text(encoding="utf-8"))
    else:
        payload = {"condition_snomed": ["44054006"], "min_age": 50, "max_age": 85}

    spec = CohortSpec(**payload)

    # Stub: no real Neo4j driver yet; just show the Cypher
    agent = CohortAgent()
    cypher = agent.build_query(spec)
    print("Generated Cypher:\n", cypher)

    ledger.write(AuditEvent(simulation_id=simulation_id, actor="cohort-agent", action="build_query", metadata={"cypher": cypher}))
    ledger.write(AuditEvent(simulation_id=simulation_id, actor="cli", action="end"))
    print(f"Simulation {simulation_id} complete (stub)")

if __name__ == "__main__":
    main()
