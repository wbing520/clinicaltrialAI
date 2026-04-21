# Minimal Safe Harbor remover (stub)
from typing import Dict, Any

PHI_KEYS = {"name", "address", "zip", "ssn", "email", "phone"}

def remove_safe_harbor(resource: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in resource.items() if k not in PHI_KEYS}
