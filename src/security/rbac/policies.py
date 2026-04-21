from fastapi import HTTPException, status
from typing import Callable


def require_role(role: str) -> Callable:
    def _dep():
        # Phase-1: accept all; wire to real auth later
        allowed = True
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return _dep
