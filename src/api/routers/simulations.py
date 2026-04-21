from fastapi import APIRouter, Depends
from ...agents.shared.messages import CohortSpec, SimulationResult, ProtocolSpec
from ...security.rbac.policies import require_role

router = APIRouter(prefix="/simulate", tags=["simulate"])

@router.post("/", response_model=SimulationResult)
async def simulate(spec: CohortSpec, _=Depends(require_role("INVESTIGATOR"))):
    from ...agents.orchestrator.runner import Orchestrator
    orch = Orchestrator()
    return orch.run(spec)
    protocol = ProtocolSpec(title="Stub Trial", primary_endpoint="All-cause hospitalization at 180 days")
    return SimulationResult(protocol=protocol, cohort_size=42, judge_score=0.65)

