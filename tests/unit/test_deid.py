from src.ingestion.deid.safe_harbor import remove_safe_harbor

def test_safe_harbor_stub():
    sample = {"name": "John Doe", "zip": "02139"}
    out = remove_safe_harbor(sample)
    assert "name" not in out
