"""Build an isolated Pages artifact against verified local storage mirrors.

This performs no upload, pointer activation, remote fetch or workflow dispatch.
The normal deployment workflow does not invoke it. See docs/STORAGE.md.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import urllib.parse

from scraper import regions
from scripts import versioned_storage as storage
from scripts.validate_data import validate_data_dir

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _pointer_url(value):
    if not isinstance(value, str):
        raise ValueError("storage pointer_url must be a string")
    url = urllib.parse.urlsplit(value)
    local = url.hostname in ("localhost", "127.0.0.1", "::1")
    if (not url.netloc or url.username or url.password or url.query or url.fragment
            or not url.path.endswith("/current.json")
            or not (url.scheme == "https" or (local and url.scheme == "http"))):
        raise ValueError("storage pointer_url must be an absolute HTTPS URL (or loopback HTTP)")
    return value


def build(*, data_root, output, storage_map=None, store=None, root=ROOT):
    """Produce a new site/report directory atomically after all checks succeed.

    ``storage_map`` maps enabled slugs to pointer URLs and optional immutable
    versions. Without an explicit version, read the local mirror's pointer once.
    The resulting catalog ALWAYS pins a verified version, never a moving pointer.
    """
    root, data_root, output = map(lambda p: pathlib.Path(p).resolve(), (root, data_root, output))
    store = pathlib.Path(store).resolve() if store is not None else None
    for source in (root, data_root, store):
        if source is not None and (output.is_relative_to(source) or source.is_relative_to(output)):
            raise ValueError("output must be outside the repository and input/store trees")
    if output.exists():
        raise ValueError("output already exists; choose a new artifact directory")
    catalog = regions.load_catalog(root / "site/regions.json")
    enabled = {entry["slug"]: entry for entry in catalog["regions"] if entry["enabled"]}
    configured = {entry["slug"] for entry in catalog["regions"]}
    if data_root.is_dir():
        unknown = {path.name for path in data_root.iterdir() if path.is_dir()} - configured
        if unknown:
            raise ValueError("unconfigured regional input directory: " + ", ".join(sorted(unknown)))
    mapping = {} if storage_map is None else storage_map
    if not isinstance(mapping, dict) or set(mapping) - set(enabled):
        raise ValueError("storage mapping may contain only enabled catalog regions")
    if mapping and store is None:
        raise ValueError("--store is required to verify external storage versions")
    if any("storage" in entry and slug not in mapping for slug, entry in enabled.items()):
        raise ValueError("source storage configuration requires an explicit verified mapping")

    output.parent.mkdir(parents=True, exist_ok=True)
    stage = pathlib.Path(tempfile.mkdtemp(prefix=".rentgen-deployment-", dir=output.parent))
    try:
        site = stage / "site"
        shutil.copytree(root / "site", site, ignore=shutil.ignore_patterns("data", "region"))
        shutil.copytree(root / "scripts/templates", stage / "scripts/templates")
        plan, reports = {}, {}
        for slug in enabled:
            if slug in mapping:
                config = mapping[slug]
                if not isinstance(config, dict):
                    raise ValueError(f"invalid storage mapping for {slug}")
                pointer_url = _pointer_url(config.get("pointer_url"))
                version = config.get("version")
                if "version" not in config:
                    pointer = json.loads((store / slug / "current.json").read_bytes())
                    if not isinstance(pointer, dict) or pointer.get("schema") != 1:
                        raise ValueError(f"invalid storage pointer for {slug}")
                    version = pointer.get("version")
                if not isinstance(version, str) or not storage.VERSION.fullmatch(version):
                    raise ValueError(f"invalid storage version for {slug}")
                directory = store / slug / "versions" / version
                verified = storage.verify(directory, slug, version)
                pinned = {"pointer_url": pointer_url, "version": version}
                plan[slug] = {"directory": str(directory), "storage": pinned}
                reports[slug] = {"backend": "external", **verified, "storage": pinned}
            else:
                source = data_root / slug
                if not source.exists():
                    continue  # canonical unpublished-region behavior
                target = site / "data" / slug
                target.mkdir(parents=True)
                for path in storage.public_files(source):
                    destination = target / path.relative_to(source)
                    destination.parent.mkdir(exist_ok=True)
                    shutil.copyfile(path, destination)
                summary = validate_data_dir(target, require_history=False)
                reports[slug] = {"backend": "pages", "bytes": summary["published_bytes"],
                                 "count": summary["count"], "files": summary["json_files"]}

        plan_path = stage / ".publication-plan.json"
        _json(plan_path, {"schema": 1, "regions": plan})
        subprocess.run(["node", str(root / "scripts/update-summary.mjs")],
                       env=os.environ | {"RENTGEN_ROOT": str(stage),
                                         "RENTGEN_PUBLICATION_PLAN": str(plan_path)},
                       check=True, capture_output=True, text=True)
        # Recheck mirrors after rendering so a disappearing/corrupted version
        # aborts the entire candidate instead of installing its catalog.
        for slug, entry in plan.items():
            storage.verify(entry["directory"], slug, entry["storage"]["version"])
            if (site / "data" / slug).exists():
                raise ValueError(f"external payload leaked into Pages artifact: {slug}")
        browser = json.loads((site / "data/regions.json").read_bytes())
        for entry in browser["regions"]:
            report = reports.get(entry["slug"])
            if report is not None:
                if not entry["published"] or entry["data"]["count"] != report["count"]:
                    raise ValueError("generated catalog does not match verified metadata")
                if report["backend"] == "external" and entry.get("storage") != report["storage"]:
                    raise ValueError("generated catalog lost the immutable version")
        plan_path.unlink()
        shutil.rmtree(stage / "scripts")
        report = {"schema": 1, "dry_run": True, "regions": reports,
                  "pages_bytes": sum(path.stat().st_size for path in site.rglob("*") if path.is_file()),
                  "external_bytes": sum(value["bytes"] for value in reports.values() if value["backend"] == "external")}
        _json(stage / "report.json", report)
        os.rename(stage, output)
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--data-root", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--store", type=pathlib.Path)
    parser.add_argument("--storage-map", type=pathlib.Path,
                        help='JSON {"schema":1,"regions":{"slaskie":{"pointer_url":"..."}}}')
    args = parser.parse_args(argv)
    try:
        mapping = {"schema": 1, "regions": {}} if args.storage_map is None else json.loads(args.storage_map.read_bytes())
        if not isinstance(mapping, dict) or mapping.get("schema") != 1 or "regions" not in mapping:
            raise ValueError("invalid storage map; require schema 1 and a regions object")
        report = build(root=args.root, data_root=args.data_root, output=args.output,
                       store=args.store, storage_map=mapping["regions"])
        print(json.dumps(report, ensure_ascii=False))
    except subprocess.CalledProcessError as exc:
        parser.exit(1, (exc.stdout or "") + (exc.stderr or "") + "\n")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"deployment dry-run: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
