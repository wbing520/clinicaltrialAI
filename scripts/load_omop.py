import json
from pathlib import Path
from typing import List
from neo4j import Driver
from src.graph.neo4j.driver import get_driver

CYPHER_CREATE = """
UNWIND $rows AS row
MERGE (p:Patient {patient_id: row.patient_id})
SET p.age = row.age
"""

def load_synthetic_patients(path: str, driver: Driver | None = None) -> int:
    fp = Path(path)
    data = json.loads(fp.read_text(encoding="utf-8"))
    rows: List[dict] = data.get("patients", [])
    drv = driver or get_driver()
    with drv.session() as s:
        s.run(CYPHER_CREATE, rows=rows)
    return len(rows)

if __name__ == "__main__":
    n = load_synthetic_patients("tests/fixtures/synthetic_patients.json")
    print(f"Loaded {n} patients")
