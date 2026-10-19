"""Local filesystem prototype of immutable regional storage and atomic pointers.

No workflow calls this module and no remote service is provisioned. Run with
``python -m scripts.versioned_storage --help``; see docs/STORAGE.md for the
object-store requirements that this single-machine rehearsal cannot prove.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import functools
import hashlib
import http.server
import json
import os
import pathlib
import re
import shutil
import tempfile
import urllib.parse

from scraper import regions
from scripts.validate_data import DataValidationError, validate_data_dir

VERSION = re.compile(r"^[a-f0-9]{64}$")
OBJECT = re.compile(r"^(?:manifest|index|archive|meta|stats|rcnstats)\.json$|^[da]/\d{2,}\.json$")


def _encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _region(store, slug):
    regions.get_region(slug)
    root = pathlib.Path(store).resolve() / slug
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextlib.contextmanager
def _locked(root):
    with (root / ".publish.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def _atomic_pointer(root, version):
    value = _encode({"schema": 1, "version": version})
    fd, temporary = tempfile.mkstemp(prefix=".pointer-", dir=root)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, root / "current.json")
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        pathlib.Path(temporary).unlink(missing_ok=True)


def verify(directory, slug, version):
    """Recheck complete bytes, inventory and payload before any pointer switch."""
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError("invalid storage version")
    root = pathlib.Path(directory)
    release_path = root / "release.json"
    if release_path.is_symlink() or _sha(release_path) != version:
        raise ValueError("release inventory hash does not match version")
    release = json.loads(release_path.read_bytes())
    if release.get("schema") != 1 or release.get("region") != slug:
        raise ValueError("release schema/region mismatch")
    files = release.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("empty release inventory")
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual != set(files) | {"release.json"}:
        raise ValueError("release files do not match inventory")
    for name, info in files.items():
        if not OBJECT.fullmatch(name):
            raise ValueError("unexpected release object path")
        path = root / name
        if (path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != root.parent)
                or not isinstance(info, dict) or path.stat().st_size != info.get("bytes")
                or _sha(path) != info.get("sha256")):
            raise ValueError(f"release object hash/size mismatch: {name}")
    summary = validate_data_dir(root, require_history=False)
    return {"version": version, "files": len(files), "bytes": summary["published_bytes"],
            "count": summary["count"], "rcn_health": (summary["rcn_health"] or {}).get("status")}


def activate(store, slug, version):
    """Roll forward/back to an already complete version; never rewrite objects."""
    root = _region(store, slug)
    with _locked(root):
        report = verify(root / "versions" / version, slug, version)
        _atomic_pointer(root, version)
        return report


def public_files(source):
    """Explicit reader inputs, excluding lifecycle history and private caches."""
    source = pathlib.Path(source)
    paths = [source / name for name in
             ("manifest.json", "index.json", "archive.json", "meta.json", "stats.json", "rcnstats.json")]
    paths += sorted((source / "d").glob("*.json"))
    if json.loads((source / "manifest.json").read_bytes()).get("schema") == 3:
        paths += sorted((source / "a").glob("*.json"))
    return paths


def publish(source, store, slug, *, interrupt_after=None):
    """Stage a public tree, validate it, seal its version, then switch current.

    ``interrupt_after`` injects an upload failure. Existing pointers/versions
    remain untouched; hidden partial uploads are removed and are never served.
    """
    source = pathlib.Path(source).resolve()
    root = _region(store, slug)
    with _locked(root):
        versions = root / "versions"
        versions.mkdir(exist_ok=True)
        stage = pathlib.Path(tempfile.mkdtemp(prefix=".upload-", dir=root))
        try:
            paths = public_files(source)
            files = {}
            for number, path in enumerate(paths, 1):
                name = path.relative_to(source).as_posix()
                destination = stage / name
                destination.parent.mkdir(exist_ok=True)
                # Copy instead of linking: a later source write cannot mutate
                # an already published immutable version.
                shutil.copyfile(path, destination)
                files[name] = {"bytes": destination.stat().st_size, "sha256": _sha(destination)}
                if interrupt_after is not None and number >= interrupt_after:
                    raise InterruptedError(f"simulated upload interruption after {number} files")
            release = _encode({"schema": 1, "region": slug, "files": files})
            (stage / "release.json").write_bytes(release)
            version = hashlib.sha256(release).hexdigest()
            report = verify(stage, slug, version)
            destination = versions / version
            if destination.exists():
                verify(destination, slug, version)  # refuse corrupted existing objects
            else:
                os.rename(stage, destination)
            _atomic_pointer(root, version)
            return report
        finally:
            if stage.exists():
                shutil.rmtree(stage)


class StorageHandler(http.server.SimpleHTTPRequestHandler):
    """Local CORS/cache policy rehearsal; only public storage paths are served."""

    def __init__(self, *args, origin, **kwargs):
        self.origin = origin
        self.immutable = False
        super().__init__(*args, **kwargs)

    def send_head(self):
        path = urllib.parse.urlsplit(self.path).path
        match = re.fullmatch(r"/[a-z]+(?:-[a-z]+)*/versions/([a-f0-9]{64})/(.+)", path)
        current = re.fullmatch(r"/[a-z]+(?:-[a-z]+)*/current\.json", path)
        if not current and not (match and (OBJECT.fullmatch(match[2]) or match[2] == "release.json")):
            self.send_error(404)
            return None
        target = pathlib.Path(self.translate_path(path))
        if not target.is_file() or any(part.is_symlink() for part in (target, *target.parents)):
            self.send_error(404)
            return None
        self.immutable = bool(match)
        return super().send_head()

    def send_error(self, *args, **kwargs):
        self.immutable = False
        super().send_error(*args, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", self.origin)
        self.send_header("Vary", "Origin")
        self.send_header("Cache-Control", "public, max-age=31536000, immutable" if self.immutable else "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=pathlib.Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    upload = sub.add_parser("publish")
    upload.add_argument("region")
    upload.add_argument("source", type=pathlib.Path)
    upload.add_argument("--interrupt-after", type=int)
    rollback = sub.add_parser("activate")
    rollback.add_argument("region")
    rollback.add_argument("version")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=8001)
    serve.add_argument("--origin", default="http://127.0.0.1:8000")
    args = parser.parse_args(argv)
    try:
        if args.command == "publish":
            print(json.dumps(publish(args.source, args.store, args.region,
                                     interrupt_after=args.interrupt_after)))
        elif args.command == "activate":
            print(json.dumps(activate(args.store, args.region, args.version)))
        else:
            origin = urllib.parse.urlsplit(args.origin)
            if origin.scheme not in ("http", "https") or not origin.netloc or origin.path or origin.query or origin.fragment:
                parser.error("--origin must be one HTTP(S) origin without a path")
            handler = functools.partial(StorageHandler, directory=str(args.store.resolve()), origin=args.origin)
            with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
                print(f"local storage listening on http://127.0.0.1:{server.server_port}", flush=True)
                server.serve_forever()
    except (OSError, ValueError, DataValidationError, regions.RegionCatalogError) as exc:
        parser.exit(1, f"storage: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
