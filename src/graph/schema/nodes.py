from typing import Iterable

PATIENT_LABEL = "Patient"
CONDITION_LABEL = "Condition"

SCHEMA_CYPHER: Iterable[str] = [
    "CREATE CONSTRAINT patient_id IF NOT EXISTS FOR (p:Patient) REQUIRE p.patient_id IS UNIQUE",
    "CREATE CONSTRAINT condition_id IF NOT EXISTS FOR (c:Condition) REQUIRE c.id IS UNIQUE",
]
