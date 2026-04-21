from typing import Dict, Any
from pydantic import BaseModel

class AuditEvent(BaseModel):
    simulation_id: str
    actor: str
    action: str
    metadata: Dict[str, Any] = {}

class AuditLedger:
    """Append-only file-backed ledger for Phase-1 dev; swap to QLDB later."""
    def __init__(self, path: str = ".audit_ledger.log"):
        self.path = path

    def write(self, event: AuditEvent) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")
