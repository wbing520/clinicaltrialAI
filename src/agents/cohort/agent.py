from typing import List
from ..shared.messages import CohortSpec
from ...graph.queries.cohort import inclusion_cypher

class CohortAgent:
    def __init__(self, neo4j_driver=None):      
        self._driver = neo4j_driver
    
    def build_query(self, spec: CohortSpec) -> str:
        return inclusion_cypher(spec)

    def materialize(self, neo4j_driver, spec: CohortSpec) -> List[str]:
        cypher = self.build_query(spec)
        params = spec.model_dump(exclude_none=True)
        with (neo4j_driver or self._driver).session() as s:
            result = s.run(cypher, **params)
            return [r["patient_id"] for r in result]



