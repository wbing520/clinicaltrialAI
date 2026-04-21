from typing import Optional
from uuid import uuid4

from ..shared.messages import CohortSpec, SimulationResult
from ..cohort.agent import CohortAgent
from ..protocol.agent import ProtocolAgent
from ..adversary.agent import AdversaryAgent
from ..judge.agent import JudgeAgent
from ...graph.rag.retriever import PgVectorRetriever
from ...security.audit_ledger.ledger import AuditLedger, AuditEvent


class Orchestrator:
    def __init__(self, ledger: Optional[AuditLedger] = None):
        self.ledger = ledger or AuditLedger()
        self.cohort = CohortAgent()
        self.protocol = ProtocolAgent(PgVectorRetriever(conn_str=""))
        self.adversary = AdversaryAgent()
        self.judge = JudgeAgent()

    def run(self, spec: CohortSpec) -> SimulationResult:
        sim_id = str(uuid4())
        self.ledger.write(AuditEvent(simulation_id=sim_id, actor="orchestrator", action="start"))

        span = (spec.max_age or 90) - (spec.min_age or 0)
        cohort_size = max(42, 1000 - max(0, (90 - span)) * 10)

        proto = self.protocol.draft_protocol("trial question stub")
        proto2 = self.adversary.perturb(proto)
        score = self.judge.score(proto2, cohort_size)

        self.ledger.write(
            AuditEvent(
                simulation_id=sim_id, actor="judge", action="score", metadata={"score": score}
            )
        )
        self.ledger.write(AuditEvent(simulation_id=sim_id, actor="orchestrator", action="end"))

        return SimulationResult(protocol=proto2, cohort_size=cohort_size, judge_score=score)
