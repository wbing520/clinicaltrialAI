from src.security.audit_ledger.ledger import AuditLedger, AuditEvent

def test_append_only_ledger(tmp_path):
    path = tmp_path / ".ledger"
    ledger = AuditLedger(str(path))
    ledger.write(AuditEvent(simulation_id="1", actor="t", action="a"))
    ledger.write(AuditEvent(simulation_id="1", actor="t2", action="b"))
    assert path.read_text(encoding="utf-8").count("\n") == 2
