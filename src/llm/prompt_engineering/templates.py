import re

RE_PHI = re.compile(r"(\b\d{3}[- ]?\d{2}[- ]?\d{4}\b|\b\d{3}-\d{4}\b|\b[A-Z][a-z]+ [A-Z][a-z]+\b)")


def sanitize_prompt(text: str) -> str:
    return RE_PHI.sub("[REDACTED]", text)
