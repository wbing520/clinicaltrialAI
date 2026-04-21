from __future__ import annotations
import os
from typing import Any, Dict, Optional

import httpx

class SmartFhirClient:
    """Minimal SMART-on-FHIR client (Phase-1 stub).

    If FHIR env vars are not set, falls back to returning sample fixtures.
    """
    def __init__(self,
                 endpoint: Optional[str] = None,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 token_url: Optional[str] = None):
        self.endpoint = endpoint or os.getenv("FHIR_ENDPOINT")
        self.client_id = client_id or os.getenv("FHIR_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("FHIR_CLIENT_SECRET")
        self.token_url = token_url or os.getenv("FHIR_TOKEN_URL")

    def _get_token(self) -> Optional[str]:
        if not (self.token_url and self.client_id and self.client_secret):
            return None
        try:
            resp = httpx.post(self.token_url, data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "system/*.read"
            }, timeout=10)
            resp.raise_for_status()
            return resp.json().get("access_token")
        except Exception:
            return None

    def fetch_bundle(self, resource: str = "Patient", params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.endpoint:
            # Fixture fallback
            from pathlib import Path
            import json
            p = Path("tests/fixtures/sample_fhir_bundle.json")
            return json.loads(p.read_text(encoding="utf-8"))
        url = f"{self.endpoint.rstrip('/')}/{resource}"
        headers = {}
        token = self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = httpx.get(url, headers=headers, params=params or {}, timeout=15)
        r.raise_for_status()
        return r.json()
