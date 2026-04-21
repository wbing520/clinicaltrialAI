import os
from uuid import uuid4
from fastapi import APIRouter, Depends
from ...agents.shared.messages import CohortSpec, SimulationResult, ProtocolSpec
from ...security.rbac.policies import require_role
from ...agents.orchestrator.runner import Orchestrator as SeqOrchestrator
from ...agents.orchestrator.graph import LangGraphOrchestrator
from ...observability.tracing import init_tracer, get_tracer

router = APIRouter(prefix="/simulate", tags=["simulate"])
init_tracer("clinicaltrial-ai-api")
tracer = get_tracer("api")

@router.post("/", response_model=SimulationResult)
async def simulate(spec: CohortSpec, _=Depends(require_role("INVESTIGATOR"))):
    use_lg = os.getenv("USE_LANGGRAPH", "true").lower() in ("1","true","yes")
    with tracer.start_as_current_span("simulate_request") as span:
        sim_id = str(uuid4())
        span.set_attribute("simulation_id", sim_id)
        if use_lg:
            orch = LangGraphOrchestrator()
            return orch.run(spec, sim_id)
        else:
            orch = SeqOrchestrator()
            return orch.run(spec)
