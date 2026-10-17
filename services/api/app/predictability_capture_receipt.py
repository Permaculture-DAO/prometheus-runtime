"""PRM-PRED-001: *offline* strict NOAA GFS capture-receipt preparation.

Does NOT perform HTTP, schedule jobs, write files, validate external signatures,
attest NOAA publication time, update Canon/Evidence Spine or authorize runtime.
Caller passes actual NOAA .idx and GRIB field response bytes for validation.

This is an engineering candidate ONLY. SHA-256 and HTTP headers are insufficient
to prove first-publication time, licence, scientific QC, or independence.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
from typing import Mapping

from .predictability_prospective_guard import (
    LEADS, WINDOW_END_EXCLUSIVE, WINDOW_START,
    PROTOCOL_ID,
)

_INDEX = re.compile(
    r"^(?P<ordinal>[0-9]+):(?P<offset>[0-9]+):d=(?P<date>[0-9]{10}):"
    r"TMP:2 m above ground:(?P<lead>[0-9]+) hour fcst:"
)
_RANGE = re.compile(r"^bytes (?P<start>[0-9]+)-(?P<end>[0-9]+)/(?P<total>[0-9]+)$")


def frozen_model_url(issue_time: datetime, lead_hours: int) -> str:
    if issue_time.tzinfo is None or issue_time.utcoffset() is None:
        raise ValueError("issue timestamp must be timezone aware")
    issue = issue_time.astimezone(timezone.utc)
    if not (WINDOW_START <= issue < WINDOW_END_EXCLUSIVE):
        raise ValueError("issue outside preregistered window")
    if (issue.hour, issue.minute, issue.second, issue.microsecond) != (0, 0, 0, 0):
        raise ValueError("only 00Z initialization permitted")
    if type(lead_hours) is not int or lead_hours not in LEADS:
        raise ValueError("lead outside preregistered set")
    return (
        f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{issue:%Y%m%d}/00/atmos/"
        f"gfs.t00z.pgrb2.0p25.f{lead_hours:03d}"
    )


def select_noaa_temperature_range(
    idx_bytes: bytes, issue_time: datetime, lead_hours: int
) -> tuple[int, int]:
    """Select exactly one indexed 2-metre TMP and next-record-exclusive end."""
    if len(idx_bytes) > 4_000_000 or len(idx_bytes) < 20:
        raise ValueError("index size outside permitted bounds")
    try:
        lines = idx_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("index is not UTF-8") from exc
    issue = issue_time.astimezone(timezone.utc)
    expected_stamp = issue.strftime("%Y%m%d%H")
    matches = []
    offsets = []
    for i, line in enumerate(lines):
        parts = line.split(":", 2)
        if len(parts) < 3 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError("malformed NOAA index entry")
        offset = int(parts[1])
        if offsets and offset <= offsets[-1]:
            raise ValueError("non-increasing NOAA index offsets")
        offsets.append(offset)
        found = _INDEX.match(line)
        if found and int(found["lead"]) == lead_hours:
            if found["date"] != expected_stamp:
                raise ValueError("forecast index has incorrect issued-at")
            matches.append(i)
    if len(matches) != 1:
        raise ValueError("expected exactly one 2m temperature field")
    at = matches[0]
    if at + 1 >= len(offsets):
        raise ValueError("missing next byte offset")
    start, stop = offsets[at], offsets[at + 1] - 1
    if start < 0 or stop < start or stop - start + 1 > 8_000_000:
        raise ValueError("GRIB field byte range invalid")
    return start, stop


def create_local_capture_receipt(
    *,
    issue_time: datetime,
    lead_hours: int,
    index_bytes: bytes,
    grib_bytes: bytes,
    grib_response_status: int,
    grib_content_range: str,
    index_response_status: int,
    index_response_headers: Mapping[str, str],
    grib_response_headers: Mapping[str, str],
    first_seen_utc: datetime,
) -> dict:
    """Validate previously fetched bytes. Does NOT acquire a file or certify timing.

    Both HTTP metadata sets are caller-provided and untrusted. Do not promote an
    observed HTTP Date, Last-Modified, ETag, or local clock into a trusted stamp.
    """
    url = frozen_model_url(issue_time, lead_hours)
    issue = issue_time.astimezone(timezone.utc)
    valid = issue + timedelta(hours=lead_hours)
    if first_seen_utc.tzinfo is None or first_seen_utc.utcoffset() is None:
        raise ValueError("local first-seen clock not timezone aware")
    observed_at = first_seen_utc.astimezone(timezone.utc)
    if not (issue <= observed_at < valid) or observed_at > issue + timedelta(hours=12):
        raise ValueError("local capture outside nominal issue-time capture window")
    start, stop = select_noaa_temperature_range(index_bytes, issue_time, lead_hours)
    match = _RANGE.fullmatch(grib_content_range)
    if grib_response_status != 206 or match is None:
        raise ValueError("NOAA GRIB field must have HTTP 206 Content-Range")
    if (int(match["start"]), int(match["end"])) != (start, stop):
        raise ValueError("HTTP byte range does not match NOAA index")
    if int(match["total"]) <= stop:
        raise ValueError("reported total length smaller than indexed byte offset")
    if len(grib_bytes) != stop - start + 1:
        raise ValueError("GRIB content length does not match indexed field")
    if not (grib_bytes.startswith(b"GRIB") and grib_bytes.endswith(b"7777")):
        raise ValueError("invalid standalone GRIB2 envelope")
    if index_response_status != 200:
        raise ValueError("NOAA index must have HTTP 200")
    def selected_headers(headers: Mapping[str, str]) -> dict:
        wanted = {"date", "last-modified", "etag", "content-length", "content-range"}
        return {k.lower(): str(v) for k, v in headers.items()
                if k.lower() in wanted and len(str(v)) < 500}
    return {
        "protocol_id": PROTOCOL_ID,
        "capture_classification": "LOCAL_CANDIDATE_UNATTESTED_NOT_ADMITTED",
        "issue_time": issue.isoformat(),
        "forecast_valid_time": valid.isoformat(),
        "lead_hours": lead_hours,
        "model_field_url": url,
        "model_index_url": url + ".idx",
        "grib_index_range": [start, stop],
        "model_index_sha256": sha256(index_bytes).hexdigest(),
        "model_field_sha256": sha256(grib_bytes).hexdigest(),
        "local_first_seen_utc": observed_at.isoformat(),
        "index_http_status": index_response_status,
        "grib_http_status": grib_response_status,
        "index_response_headers_untrusted": selected_headers(index_response_headers),
        "grib_response_headers_untrusted": selected_headers(grib_response_headers),
        "original_noaa_source_independently_verified": False,
        "source_publication_time_attested": False,
        "independent_external_timestamp_attested": False,
        "model_implementation_version_verified": False,
        "station_observation_available": False,
        "human_scientific_approval": False,
        "source_registry_admitted": False,
        "prospective_scientific_event_certified": False,
        "land_credit_insurance_authority": False,
        "production_runtime_modified": False,
    }
