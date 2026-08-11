"""Shared HTTP session that politely backs off on refusals.

Portals (especially nieruchomosci-online's many sub-domains) return HTTP 429
"Too Many Requests" when hit too fast. This session auto-retries 429/405/5xx
with exponential back-off and honours any ``Retry-After`` header — but CAPPED:
a portal once answered with a Retry-After so large that urllib3 slept for
hours inside one request and the CI job hit its 6-hour kill switch. A capped
wait keeps every request's worst case bounded; if the portal is still angry
after the retries, the caller's error handling drops that page and moves on.

405 is in the list because that is the shape Otodom's refusal takes. In runs
31408840562 and 31422141701 the `300k-400k` price band died at page 5 with
`405 Client Error: Not Allowed` and the next seven bands died on page 1 — then
the eighth was served normally. A transient refusal, not a rejected method:
the scraper only ever issues GETs on URLs that answer GET, so a 405 here means
"not you, not now". Retrying it costs ~30 s of back-off in the worst case and
buys back seven whole price bands' worth of coverage.
"""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover - very old urllib3
    from requests.packages.urllib3.util.retry import Retry

RETRY_AFTER_CAP = 90.0   # seconds; longest single Retry-After sleep we honour
# Every status worth asking again about. 405: see the module docstring.
RETRY_STATUSES = (405, 429, 500, 502, 503, 504)


class CappedRetry(Retry):
    def get_retry_after(self, response):
        ra = super().get_retry_after(response)
        return min(ra, RETRY_AFTER_CAP) if ra is not None else ra


def session() -> requests.Session:
    s = requests.Session()
    retry = CappedRetry(
        total=5,
        status_forcelist=RETRY_STATUSES,
        backoff_factor=2,          # sleeps ~0, 2, 4, 8, 16 s between tries
        respect_retry_after_header=True,
        raise_on_status=False,     # return the final response; caller decides
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s
