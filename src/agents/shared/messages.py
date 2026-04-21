from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class CohortSpec(BaseModel):
    condition_snomed: List[str] = Field(default_factory=list)
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    include_medications_rxnorm: List[str] = Field(default_factory=list)
    exclude_comorbid_snomed: List[str] = Field(default_factory=list)

class ProtocolSpec(BaseModel):
    title: str
    primary_endpoint: str
    secondary_endpoints: List[str] = Field(default_factory=list)
    followup_days: int = 180

class SimulationResult(BaseModel):
    protocol: ProtocolSpec
    cohort_size: int
    judge_score: float
    adverse_event_risk: Optional[float] = None

class AgentMessage(BaseModel):
    simulation_id: str
    role: Literal['cohort','protocol','adversary','judge']
    payload: dict
