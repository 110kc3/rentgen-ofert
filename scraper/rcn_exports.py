"""Validated provincial RCN exports used when the live WFS cannot be traversed.

GUGiK's own QGIS client uses these GeoParquet files for voivodeship downloads.
Read only the matching fields, never publish the original export or geometry.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import pathlib
import re
import tempfile
import time

import pyarrow.parquet as pq
import requests

from . import rcn

EXPORT_BASE = ("https://opendata.geoportal.gov.pl/InneDane/latest_exports/"
               "rcn_transakcje_ceny/PARQUET/")
MAX_EXPORT_BYTES = 512 * 1024 * 1024
DOWNLOAD_ATTEMPTS = 3


class IncompleteExportError(ValueError):
    pass


def _download(session, url, path, log):
    """Retry interrupted streams as whole files, never append to a partial file.

    Requests' adapter retries stop once streaming response headers arrive.
    Parsing and data validation stay outside this retry loop: corrupt data is
    not a transient transport error and must never replace the previous cache.
    """
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        size, digest = 0, hashlib.sha256()
        try:
            with session.get(url, headers=rcn.HEADERS,
                             timeout=rcn.REQUEST_TIMEOUT, stream=True) as response:
                response.raise_for_status()
                declared = response.headers.get("Content-Length")
                if declared is not None and not 0 < int(declared) <= MAX_EXPORT_BYTES:
                    raise ValueError("RCN export: invalid download size")
                with path.open("wb") as output:
                    for chunk in response.iter_content(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_EXPORT_BYTES:
                            raise ValueError("RCN export: download too large")
                        output.write(chunk)
                        digest.update(chunk)
                if declared is not None and size != int(declared):
                    raise IncompleteExportError("RCN export: interrupted download")
            return size, digest.hexdigest()
        except (requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError, IncompleteExportError) as exc:
            path.unlink(missing_ok=True)
            if attempt == DOWNLOAD_ATTEMPTS:
                raise
            log(f"RCN export: download attempt {attempt}/{DOWNLOAD_ATTEMPTS} "
                f"failed ({exc}); restarting {url}")
            time.sleep(2 * attempt)


def _read_export(path, region, layer, props, compact):
    parquet = pq.ParquetFile(path)
    names = {name.lower(): name for name in parquet.schema_arrow.names}
    required = {"gid", *props.split(",")}
    if len(names) != len(parquet.schema_arrow.names) or not required <= names.keys():
        raise ValueError(f"RCN export {layer}: missing or ambiguous fields")
    if parquet.metadata.num_rows <= 0:
        raise ValueError(f"RCN export {layer}: empty layer")
    records, seen, read = [], set(), 0
    for batch in parquet.iter_batches(batch_size=8192,
                                     columns=[names[k] for k in sorted(required)]):
        for original in batch.to_pylist():
            row = {k.lower(): v for k, v in original.items()}
            ident = row["gid"]
            if type(ident) is not int or ident < 0 or ident in seen:
                raise ValueError(f"RCN export {layer}: invalid or duplicate feature ID")
            seen.add(ident)
            if not isinstance(row["teryt"], str) or not row["teryt"].startswith(region):
                raise ValueError(f"RCN export {layer}: foreign or missing TERYT")
            read += 1
            row = {k: ("" if v is None else v.isoformat()
                       if isinstance(v, (dt.date, dt.datetime)) else str(v))
                   for k, v in row.items()}
            if layer == "budynki" and row["bud_rodzaj"] != "mieszkalny":
                continue
            record = compact(row)
            if record:
                # Preserve distinct source IDs, even when compact deeds coincide.
                records.append(record)
    if read != parquet.metadata.num_rows or not records:
        raise ValueError(f"RCN export {layer}: incomplete or unusable layer")
    return records, read


def fetch_exports(session, region, log=print):
    if not re.fullmatch(r"\d{2}", region):
        raise ValueError("RCN export: expected a two-digit voivodeship TERYT")
    layers, sources = {}, {}
    with tempfile.TemporaryDirectory(prefix="rentgen-rcn-") as directory:
        for layer, props, compact in (("lokale", rcn.LOK_PROPS, rcn._compact_lok),
                                      ("budynki", rcn.BUD_PROPS, rcn._compact_bud)):
            url = f"{EXPORT_BASE}{region}_transakcje_ceny_{layer}.parquet"
            path = pathlib.Path(directory) / f"{layer}.parquet"
            size, digest = _download(session, url, path, log)
            records, raw = _read_export(path, region, layer, props, compact)
            layers[layer] = records
            sources[layer] = {"url": url, "sha256": digest,
                              "bytes": size, "rows": raw}
            log(f"RCN export {layer}: {raw} source rows, {len(records)} usable transactions")
    return layers["lokale"], layers["budynki"], {"kind": "gugik_exports", "files": sources}
