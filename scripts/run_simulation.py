import json
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from src.agents.cohort.agent import CohortAgent
from src.agents.shared.messages import CohortSpec
from src.security.audit_ledger.ledger import AuditLedger, AuditEvent


def _read_json_any_encoding(path: Path) -> Dict[str, Any]:
    data = path.read_bytes()
    # Detect common BOMs / encodings
    if data.startswith(b"\xef\xbb\xbf"):
        text = data.decode("utf-8-sig")
    elif data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        # UTF-16 (LE/BE) — Python can infer endianness from BOM
        text = data.decode("utf-16")
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            # Last resort
            text = data.decode("utf-8", errors="ignore")
    return json.loads(text)


# This CLI simulates the vertical slice using stubbed data

def main() -> None:
    simulation_id = str(uuid4())
    ledger = AuditLedger()
    ledger.write(AuditEvent(simulation_id=simulation_id, actor="cli", action="start"))

    # Load a tiny synthetic cohort spec fixture
    spec_path = Path("tests/fixtures/sample_protocol.json")
    if spec_path.exists():
        payload: Dict[str, Any] = _read_json_any_encoding(spec_path)
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
