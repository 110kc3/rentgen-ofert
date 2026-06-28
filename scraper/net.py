"""Shared HTTP session that politely backs off on rate limiting.

Portals (especially nieruchomosci-online's many sub-domains) return HTTP 429
"Too Many Requests" when hit too fast. This session auto-retries 429/503/5xx
with exponential back-off and honours any ``Retry-After`` header, so a transient
rate-limit pauses-and-retries instead of dropping the whole portal.
"""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover - very old urllib3
    from requests.packages.urllib3.util.retry import Retry


def session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=5,
        status_forcelist=(429, 500, 502, 503, 504),
        backoff_factor=2,          # sleeps ~0, 2, 4, 8, 16 s between tries
        respect_retry_after_header=True,
        raise_on_status=False,     # return the final response; caller decides
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s
