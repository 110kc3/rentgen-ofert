"""Safe staging and deploy overlay operations for one regional data branch.

Both workflows call this module, so their isolation rules are executable and
fixture-testable instead of living only in shell comments.  A data branch may
contain exactly its own dataset and per-region caches.  ``geo_cache.json`` and
``nol_towns.json`` are intentionally shared logical maps; each regional branch
can carry a fork, and their entries are themselves region-scoped.
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess

from scraper import regions


class RegionStorageError(RuntimeError):
    pass


SHARED_CACHES = (
    pathlib.PurePosixPath("cache/geo_cache.json"),
    pathlib.PurePosixPath("cache/nol_towns.json"),
)


def _git(root, *args, check=True):
    return subprocess.run(
        ["git", *args], cwd=root, check=check,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def _entry(root, region):
    document = regions.load_catalog(pathlib.Path(root) / "site" / "regions.json")
    return regions.get_region(region, document)


def allowed_index_paths(region):
    """Exact files/prefix allowed in a ``data-<region>`` orphan commit."""
    return {
        *SHARED_CACHES,
        pathlib.PurePosixPath(f"cache/nol_archive_{region}.json"),
        pathlib.PurePosixPath(f"cache/phash_{region}.json.gz"),
        pathlib.PurePosixPath(f"cache/rcn_{region}.json.gz"),
    }


def _allowed(path, region):
    candidate = pathlib.PurePosixPath(path)
    data_root = pathlib.PurePosixPath("site/data") / region
    return candidate == data_root or data_root in candidate.parents \
        or candidate in allowed_index_paths(region)


def stage_region(root, region):
    """Stage only ``region`` data/caches in the current (normally orphan) index.

    Returns the complete staged path list and refuses to continue if the index
    carries anything outside the allowlist.  The caller owns creating/clearing
    the orphan index before this function runs.
    """
    root = pathlib.Path(root).resolve()
    _entry(root, region)
    data_dir = root / "site" / "data" / region
    if not data_dir.is_dir():
        raise RegionStorageError(f"regional data directory does not exist: {data_dir}")

    candidates = [pathlib.PurePosixPath("site/data") / region,
                  *allowed_index_paths(region)]
    for relative in candidates:
        if (root / relative).exists():
            _git(root, "add", "-f", "--", relative.as_posix())

    raw = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    staged = [value.decode("utf-8") for value in raw.split(b"\0") if value]
    unexpected = [path for path in staged if not _allowed(path, region)]
    if unexpected:
        raise RegionStorageError(
            "regional data index contains out-of-scope path(s): "
            + ", ".join(unexpected))
    if not any(path == f"site/data/{region}" or
               path.startswith(f"site/data/{region}/") for path in staged):
        raise RegionStorageError(f"no site/data/{region} files were staged")
    return staged


def overlay_region(root, ref, region):
    """Replace one deployed region from ``ref`` without touching siblings.

    A ref that does not actually contain its regional directory is a no-op;
    this preserves any copy seeded from the legacy shared data branch.
    Returns whether an overlay occurred.
    """
    root = pathlib.Path(root).resolve()
    _entry(root, region)
    relative = f"site/data/{region}"
    exists = _git(root, "cat-file", "-e", f"{ref}:{relative}",
                  check=False)
    if exists.returncode:
        return False
    destination = root / relative
    if destination.exists():
        shutil.rmtree(destination)
    _git(root, "checkout", ref, "--", relative)
    return True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="isolate regional data branches")
    parser.add_argument("--root", default=".", help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("stage", help="stage one region for an orphan branch")
    stage.add_argument("region")
    overlay = sub.add_parser("overlay", help="overlay one region from a git ref")
    overlay.add_argument("ref")
    overlay.add_argument("region")
    args = parser.parse_args(argv)
    try:
        if args.command == "stage":
            staged = stage_region(args.root, args.region)
            print(f"staged {len(staged)} path(s) for {args.region}")
        else:
            changed = overlay_region(args.root, args.ref, args.region)
            if changed:
                print(f"overlaid {args.region} from {args.ref}")
            else:
                print(f"{args.ref} carries no site/data/{args.region} — "
                      "leaving the deployed copy intact")
    except (regions.RegionCatalogError, RegionStorageError,
            subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
