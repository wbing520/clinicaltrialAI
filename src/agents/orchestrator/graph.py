from typing import Any, Dict
import os
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from ..shared.messages import CohortSpec, SimulationResult, ProtocolSpec
from ..cohort.agent import CohortAgent
from ..protocol.agent import ProtocolAgent
from ..adversary.agent import AdversaryAgent
from ..judge.agent import JudgeAgent
from ...graph.rag.retriever import PgVectorRetriever
from ...graph.neo4j.driver import get_driver
from ...security.audit_ledger.ledger import AuditLedger, AuditEvent
from ...observability.tracing import init_tracer, get_tracer

class OrchestratorState(BaseModel):
    spec: CohortSpec
    cohort_size: int | None = None
    protocol: ProtocolSpec | None = None
    judge_score: float | None = None
    simulation_id: str

class LangGraphOrchestrator:
    def __init__(self, ledger: AuditLedger | None = None):
        init_tracer()
        self.tracer = get_tracer("orchestrator")
        self.ledger = ledger or AuditLedger()
        self.cohort = CohortAgent(neo4j_driver=get_driver())
        self.protocol = ProtocolAgent(PgVectorRetriever(conn_str=os.getenv("PG_CONN","")))
        self.adversary = AdversaryAgent()
        self.judge = JudgeAgent()
        self.graph = self._build()

    def _build(self):
        sg = StateGraph(OrchestratorState)
        sg.add_node("cohort", self._cohort_node)
        sg.add_node("protocol", self._protocol_node)
        sg.add_node("adversary", self._adversary_node)
        sg.add_node("judge", self._judge_node)
        sg.set_entry_point("cohort")
        sg.add_edge("cohort", "protocol")
        sg.add_edge("protocol", "adversary")
        sg.add_edge("adversary", "judge")
        sg.add_edge("judge", END)
        return sg.compile()

    def _cohort_node(self, state: OrchestratorState) -> Dict[str, Any]:
        with self.tracer.start_as_current_span("cohort") as span:
            span.set_attribute("simulation_id", state.simulation_id)
            # For Phase-1, estimate or query if graph loaded; try query, else fallback
            try:
                cypher = self.cohort.build_query(state.spec)
                with get_driver().session() as s:
                    res = [r["patient_id"] for r in s.run(cypher, **state.spec.model_dump(exclude_none=True))]
                size = len(res)
            except Exception:
                span.set_attribute("warning", "neo4j_unavailable")
                span.add_event("fallback_estimation")
                span_val = (state.spec.max_age or 90) - (state.spec.min_age or 0)
                size = max(42, 1000 - max(0, (90 - span_val)) * 10)
            self.ledger.write(AuditEvent(simulation_id=state.simulation_id, actor="cohort", action="size", metadata={"size": size}))
            return {"cohort_size": size}

    def _protocol_node(self, state: OrchestratorState) -> Dict[str, Any]:
        with self.tracer.start_as_current_span("protocol") as span:
            span.set_attribute("simulation_id", state.simulation_id)
            proto = self.protocol.draft_protocol("trial question stub")
            self.ledger.write(AuditEvent(simulation_id=state.simulation_id, actor="protocol", action="draft"))
            return {"protocol": proto}

    def _adversary_node(self, state: OrchestratorState) -> Dict[str, Any]:
        with self.tracer.start_as_current_span("adversary") as span:
            span.set_attribute("simulation_id", state.simulation_id)
            perturbed = self.adversary.perturb(state.protocol)  # type: ignore[arg-type]
            self.ledger.write(AuditEvent(simulation_id=state.simulation_id, actor="adversary", action="perturb"))
            return {"protocol": perturbed}

    def _judge_node(self, state: OrchestratorState) -> Dict[str, Any]:
        with self.tracer.start_as_current_span("judge") as span:
            span.set_attribute("simulation_id", state.simulation_id)
            score = self.judge.score(state.protocol, state.cohort_size or 0)  # type: ignore[arg-type]
            self.ledger.write(AuditEvent(simulation_id=state.simulation_id, actor="judge", action="score", metadata={"score": score}))
            return {"judge_score": score}

    def run(self, spec: CohortSpec, simulation_id: str) -> SimulationResult:
        with self.tracer.start_as_current_span("orchestrate") as span:
            span.set_attribute("simulation_id", simulation_id)
            initial = OrchestratorState(spec=spec, simulation_id=simulation_id)
            final: OrchestratorState = self.graph.invoke(initial)
            return SimulationResult(protocol=final.protocol, cohort_size=final.cohort_size or 0, judge_score=final.judge_score or 0.0)
