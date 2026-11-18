from __future__ import annotations

import datetime as dt
import os
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scraper.regions import catalog
from scripts.schedule_region import read_previous, timestamp

MAXIMUM_PUBLICATION_AGE = {
    "twice_daily": dt.timedelta(hours=36),
    "daily": dt.timedelta(hours=48),
    "every_72h": dt.timedelta(hours=120),
    "weekly": dt.timedelta(days=9),
}


def monitored_regions(document):
    return [entry for entry in document["regions"]
            if entry["enabled"] and entry["cadence"] in MAXIMUM_PUBLICATION_AGE]


def publication_problem(entry, now, read_meta):
    try:
        meta = read_meta(entry["slug"])
        updated = timestamp(meta["updated"], now)
    except Exception as exc:
        return f"publication metadata unreadable ({type(exc).__name__}: {exc})"
    allowed = MAXIMUM_PUBLICATION_AGE[entry["cadence"]]
    age = now - updated
    if age > allowed:
        return (f"last published {updated.isoformat()}, {format_age(age)} ago; "
                f"{entry['cadence']} allows {format_age(allowed)}")
    return None


def format_age(age):
    return f"{age.total_seconds() / 3600:.1f}h"


def freshness_report(document, now, read_meta):
    return {entry["slug"]: publication_problem(entry, now, read_meta)
            for entry in monitored_regions(document)}


def render_report(report):
    lines = ["### Publication freshness", ""]
    for slug, problem in report.items():
        lines.append(f"- {slug}: {'STALE — ' + problem if problem else 'fresh'}")
    return "\n".join(lines) + "\n"


def main(document=None, now=None, read_meta=None):
    document = catalog() if document is None else document
    now = dt.datetime.now(dt.timezone.utc) if now is None else now
    if read_meta is None:
        repository = os.environ["GITHUB_REPOSITORY"]
        read_meta = lambda region: read_previous(repository, region)
    report = freshness_report(document, now, read_meta)
    rendered = render_report(report)
    print(rendered, end="")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with pathlib.Path(summary_path).open("a") as summary:
            summary.write(rendered)
    return 1 if any(report.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
