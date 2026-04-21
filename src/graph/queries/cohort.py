from typing import List
from ...agents.shared.messages import CohortSpec

# Simplified Cypher builders for the vertical slice

def inclusion_cypher(spec: CohortSpec) -> str:
    parts: List[str] = [
        "MATCH (p:Patient)",
        "OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c:Condition)",
        "WITH p, collect(distinct c.snomed) as conds"
    ]
    where_clauses: List[str] = []
    if spec.condition_snomed:
        where_clauses.append(f"any(x IN $condition_snomed WHERE x IN conds)")
    if spec.min_age is not None:
        where_clauses.append("p.age >= $min_age")
    if spec.max_age is not None:
        where_clauses.append("p.age <= $max_age")
    if where_clauses:
        parts.append("WHERE " + " AND ".join(where_clauses))
    parts.append("RETURN p.patient_id as patient_id LIMIT 1000")
    return "\n".join(parts)

