"""Choose one scrape under the global workflow lock; no portal requests.

The hourly Opolskie tick checks the last successful data-branch publication.
It never bootstraps a missing pilot or treats unavailable metadata as overdue.
Manual dispatches deliberately bypass the cadence, but not region validation.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import re
import urllib.request

from scraper.regions import catalog, get_region, RegionCatalogError

SLASKIE_CRON = "0 6,18 * * *"
OPOLSKIE_CRON = "17 * * * *"
INTERVAL = dt.timedelta(hours=72)


def read_api(repository, path, accept="application/vnd.github+json"):
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("invalid GitHub repository")
    url = f"https://api.github.com/repos/{repository}/{path}"
    headers = {"Accept": accept,
               "User-Agent": "rentgen-schedule"}
    token = os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def read_previous(repository, region):
    return read_api(repository, f"contents/site/data/{region}/meta.json?ref=data-{region}",
                    "application/vnd.github.raw+json")


def timestamp(value, now):
    if not isinstance(value, str):
        raise ValueError("cadence timestamp must be a string")
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("cadence timestamp must include a timezone")
    if parsed > now:
        raise ValueError("cadence timestamp is in the future")
    return parsed


def read_last_attempt(repository, region):
    # Seven-day retention means at most a few automatic attempts. Fail closed
    # if manual activity exceeds a page; never silently ignore a recent attempt.
    data = read_api(repository, f"actions/artifacts?name=cadence-attempt-{region}&per_page=100")
    artifacts = data["artifacts"]
    if data["total_count"] != len(artifacts):
        raise ValueError("incomplete cadence attempt history")
    return [a["created_at"] for a in artifacts]


def decide(event, schedule, requested, document, now, previous, attempts=lambda _: []):
    """Return (region, run, reason). ``previous`` reads only publication metadata."""
    if event == "schedule":
        if schedule == SLASKIE_CRON:
            slug, cadence = "slaskie", "twice_daily"
        elif schedule == OPOLSKIE_CRON:
            slug, cadence = "opolskie", "every_72h"
        else:
            raise ValueError(f"unknown schedule: {schedule!r}")
        entry = get_region(slug, document)
        if not entry["enabled"] or entry["cadence"] != cadence:
            return slug, False, "disabled or no longer on this cadence"
        if cadence == "every_72h":
            meta = previous(slug)
            if not isinstance(meta, dict) or not isinstance(meta.get("updated"), str):
                raise ValueError("previous publication needs an updated timestamp")
            updated = timestamp(meta["updated"], now)
            due = updated + INTERVAL
            if now < due:
                return slug, False, f"next eligible refresh: {due.isoformat()}"
            attempted = [timestamp(value, now) for value in attempts(slug)]
            if attempted and now < max(attempted) + INTERVAL:
                return slug, False, f"attempt cooldown until {(max(attempted) + INTERVAL).isoformat()}"
            return slug, True, f"72 hours elapsed since publication and last attempt ({updated.isoformat()})"
        return slug, True, "twice-daily schedule"
    if event not in ("push", "workflow_dispatch"):
        raise ValueError(f"unsupported event: {event!r}")
    slug = (requested or document["default"]) if event == "workflow_dispatch" else document["default"]
    entry = get_region(slug, document)
    if not entry["enabled"]:
        raise RegionCatalogError(f"region {slug!r} is disabled")
    return slug, True, "manual dispatch" if event == "workflow_dispatch" else "code update"


def main():
    slug, run, reason = decide(
        os.environ["GITHUB_EVENT_NAME"], os.environ.get("SCHEDULE", ""),
        os.environ.get("REQUESTED_REGION", ""), catalog(), dt.datetime.now(dt.timezone.utc),
        lambda region: read_previous(os.environ["GITHUB_REPOSITORY"], region),
        lambda region: read_last_attempt(os.environ["GITHUB_REPOSITORY"], region),
    )
    message = f"{slug}: {'refresh' if run else 'skip'} — {reason}"
    print(message)
    with pathlib.Path(os.environ["GITHUB_OUTPUT"]).open("a") as output:
        output.write(f"run={str(run).lower()}\n")
    with pathlib.Path(os.environ["GITHUB_ENV"]).open("a") as env:
        env.write(f"REGION={slug}\nDATA_BRANCH=data-{slug}\n")
    with pathlib.Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as summary:
        summary.write(f"### Schedule decision\n\n{message}\n")


if __name__ == "__main__":
    main()
