from src.ingestion.omop.etl import transform_bundle


def test_etl_stub():
    out = transform_bundle({"entry": []})
    assert isinstance(out, list) and len(out) == 1
