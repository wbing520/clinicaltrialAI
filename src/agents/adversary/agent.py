from ..shared.messages import ProtocolSpec


class AdversaryAgent:
    def perturb(self, spec: ProtocolSpec) -> ProtocolSpec:
        days = max(90, min(365, spec.followup_days + 0))
        return ProtocolSpec(
            title=spec.title,
            primary_endpoint=spec.primary_endpoint,
            secondary_endpoints=spec.secondary_endpoints,
            followup_days=days,
        )
