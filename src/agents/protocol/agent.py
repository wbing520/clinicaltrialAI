from ..shared.messages import ProtocolSpec
from ...graph.rag.retriever import PgVectorRetriever


class ProtocolAgent:
    def __init__(self, retriever: PgVectorRetriever):
        self.retriever = retriever

    def draft_protocol(self, question: str) -> ProtocolSpec:
        _ = self.retriever.search(question, k=3)
        return ProtocolSpec(
            title="Phase II Trial (Stub)",
            primary_endpoint="All-cause hospitalization at 180 days",
            secondary_endpoints=["CV mortality", "Quality of life score"],
            followup_days=180,
        )
