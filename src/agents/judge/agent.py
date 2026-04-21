from ..shared.messages import ProtocolSpec


class JudgeAgent:
    def score(self, spec: ProtocolSpec, cohort_size: int) -> float:
        base = 0.5
        if 100 <= cohort_size <= 1000:
            base += 0.2
        if spec.followup_days >= 180:
            base += 0.1
        return min(0.95, base)
