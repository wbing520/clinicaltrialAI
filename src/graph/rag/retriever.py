from typing import List
from pydantic import BaseModel

class RetrievedDoc(BaseModel):
    id: str
    score: float
    text: str

class PgVectorRetriever:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    def search(self, query: str, k: int = 5) -> List[RetrievedDoc]:
        # Placeholder: return stubbed docs for Phase-1 slice
        return [RetrievedDoc(id=f"doc-{i}", score=1.0/(i+1), text=f"Protocol precedent {i}") for i in range(k)]
