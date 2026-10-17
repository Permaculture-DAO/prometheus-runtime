"""PRM-PRED prospective first-seen receipt screening; NO trusted-time attestation.

A protocol frozen on a candidate branch is not an approved scientific
preregistration. These checks merely refuse obviously nonprospective events.
All caller-supplied timestamps and source identities remain UNAUTHENTICATED.
No network, scheduling, Holochain, database, capital, or public runtime writes.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pydantic import BaseModel, Field, ConfigDict, model_validator

PROTOCOL_ID = "PRM-PRED-PROSPECTIVE-001@0.1-CANDIDATE"
PROTOCOL_FREEZE_GIT_COMMIT = "d8eda9b5994f162f56f27f3b5f82bbe78b97ac3e"
WINDOW_START = datetime(2026, 10, 20, tzinfo=timezone.utc)
WINDOW_END_EXCLUSIVE = datetime(2027, 1, 20, tzinfo=timezone.utc)
SITE_IDS = frozenset(("USW00012839", "USW00013874", "USW00013889"))
LEADS = frozenset((24, 48, 72))


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class CaptureReceipt(Strict):
    """A LOCAL record; independently timestamped/public source claim is prohibited."""
    source_url: str = Field(min_length=12, max_length=2048)
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    first_seen_utc: datetime
    local_receipt_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def check_utc(self):
        if self.first_seen_utc.tzinfo is None or self.first_seen_utc.utcoffset() is None:
            raise ValueError("first-seen timestamp must carry a timezone")
        return self


class ProspectiveEvent(Strict):
    protocol_id: str
    model_id: str
    site_id: str
    issue_time: datetime
    valid_time: datetime
    lead_hours: int
    model_field: CaptureReceipt
    model_index: CaptureReceipt
    station_observation: CaptureReceipt | None = None
    station_observed_at: datetime | None = None
    normal_file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_kind: str = "NOAA_1991_2020_HOURLY_NORMAL"
    persistence_snapshot: CaptureReceipt | None = None
    persistence_observed_at: datetime | None = None
    station_qc_reviewed: bool = False

    @model_validator(mode="after")
    def check_schema(self):
        times = (self.issue_time, self.valid_time, self.station_observed_at,
                 self.persistence_observed_at)
        if any(t is not None and (t.tzinfo is None or t.utcoffset() is None) for t in times):
            raise ValueError("all timestamps require an explicit timezone")
        if self.station_observation is None and self.station_observed_at is not None:
            raise ValueError("station timestamp without station source record")
        if self.station_observation is not None and self.station_observed_at is None:
            raise ValueError("station source record without observation time")
        if self.persistence_snapshot is None and self.persistence_observed_at is not None:
            raise ValueError("persistence observation time without snapshot")
        if self.persistence_snapshot is not None and self.persistence_observed_at is None:
            raise ValueError("persistence snapshot without observation time")
        return self


def screen_event(event: ProspectiveEvent) -> dict:
    """Only classify input chronology; never trust/endorse external provenance.

    No caller field can set first-seen authentication or scientific certification.
    A successful chronological screen is *not* actual evidence of pre-target capture.
    """
    reasons = []
    if event.protocol_id != PROTOCOL_ID:
        reasons.append("PROTOCOL_ID_MISMATCH")
    if event.model_id != "NOAA_GFS_0p25":
        reasons.append("MODEL_OUTSIDE_PROTOCOL")
    if event.site_id not in SITE_IDS:
        reasons.append("STATION_OUTSIDE_FROZEN_UNIVERSE")
    if event.lead_hours not in LEADS:
        reasons.append("LEAD_OUTSIDE_FROZEN_UNIVERSE")
    issue = event.issue_time.astimezone(timezone.utc)
    target = event.valid_time.astimezone(timezone.utc)
    if not (WINDOW_START <= issue < WINDOW_END_EXCLUSIVE):
        reasons.append("ISSUE_OUTSIDE_FROZEN_WINDOW")
    if (issue.hour,issue.minute,issue.second,issue.microsecond)!=(0,0,0,0):
        reasons.append("NOT_00Z_ISSUE")
    if target <= issue or abs((target-issue).total_seconds()/3600-event.lead_hours)>1e-9:
        reasons.append("TARGET_LEAD_MISMATCH")
    captures = (event.model_field, event.model_index)
    for receipt in captures:
        first = receipt.first_seen_utc.astimezone(timezone.utc)
        if first < issue:
            reasons.append("SOURCE_FIRST_SEEN_BEFORE_NOMINAL_INIT")
        if first > issue + timedelta(hours=12):
            reasons.append("MODEL_CAPTURE_MORE_THAN_12H_AFTER_ISSUE")
        if first >= target:
            reasons.append("MODEL_CAPTURE_AFTER_FORECAST_VALIDITY")
    expected = (
        f"https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.{issue:%Y%m%d}/00/atmos/"
        f"gfs.t00z.pgrb2.0p25.f{event.lead_hours:03d}"
    )
    if event.model_field.source_url != expected:
        reasons.append("GFS_FIELD_NOT_FROZEN_PRODUCT")
    if event.model_index.source_url != expected + ".idx":
        reasons.append("GFS_INDEX_NOT_FROZEN_PRODUCT")
    # Matching snapshots does not establish source publication timing.
    if event.station_observation is not None:
        record = event.station_observation
        if record.first_seen_utc < event.station_observed_at:
            reasons.append("OBS_CAPTURE_BEFORE_MEASUREMENT")
        if event.station_observed_at < target - timedelta(minutes=60) or event.station_observed_at > target + __import__("datetime").timedelta(minutes=60):
            reasons.append("STATION_TIME_MISMATCH")
        if not record.source_url.startswith("https://noaa-ghcnh-pds.s3.amazonaws.com/"):
            reasons.append("STATION_SOURCE_URL_UNEXPECTED")
    if event.baseline_kind != "NOAA_1991_2020_HOURLY_NORMAL":
        reasons.append("PRIMARY_BASELINE_MUST_BE_CLIMATE_NORMAL")
    persistence_eligible = False
    if event.persistence_snapshot is not None:
        snap=event.persistence_snapshot
        assert event.persistence_observed_at is not None
        if event.persistence_observed_at > issue:
            reasons.append("PERSISTENCE_MEASUREMENT_AFTER_ISSUE")
        # Need proven public availability before issuance, not just before target.
        if snap.first_seen_utc >= issue:
            reasons.append("PERSISTENCE_SNAPSHOT_NOT_CAPTURED_BEFORE_ISSUE")
        elif event.persistence_observed_at <= snap.first_seen_utc:
            persistence_eligible = True  # Only LOCAL timestamp-consistent, NOT independently verified.
        else:
            reasons.append("PERSISTENCE_SNAPSHOT_BEFORE_MEASUREMENT")
    digest = sha256(json.dumps(event.model_dump(mode="json"), sort_keys=True,
                               separators=(",", ":"),allow_nan=False).encode("utf-8")).hexdigest()
    status = "HOLD_INVALID_LOCAL_CHRONOLOGY" if reasons else (
        "LOCAL_CHRONOLOGY_PLAUSIBLE_UNVERIFIED" if event.station_observation is not None
        else "HOLD_OBSERVATION_NOT_AVAILABLE"
    )
    return {
        "protocol_id":PROTOCOL_ID,"protocol_candidate_git_commit":PROTOCOL_FREEZE_GIT_COMMIT,
        "event_sha256":digest,"status":status,"failure_codes":sorted(set(reasons)),
        "local_persistence_chronology_plausible":persistence_eligible,
        "forecast_source_authenticity_verified":False,
        "first_seen_time_independently_attested":False,
        "observation_qc_independently_verified":False,
        "reviewed_for_scientific_admission":False,
        "validated_horizon_hours":None,
        "public_runtime_activation_authorized":False,
        "land_capital_insurance_authority":False,
        "mode":"SHADOW_ONLY",
    }


def prospective_schedule() -> dict:
    """Frozen cohort independent of NOAA availability, forecasts and outcomes."""
    from datetime import timedelta
    date=WINDOW_START
    planned=[]
    while date<WINDOW_END_EXCLUSIVE:
        for site in sorted(SITE_IDS):
            for lead in sorted(LEADS):
                planned.append({"issue_time":date.isoformat(),"site_id":site,
                                "lead_hours":lead,"valid_time":(date+timedelta(hours=lead)).isoformat()})
        date += timedelta(days=1)
    digest=sha256(json.dumps(planned,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {
        "protocol_id":PROTOCOL_ID,"frozen_candidate_commit":PROTOCOL_FREEZE_GIT_COMMIT,
        "issue_days":92,"planned_events":len(planned),"schedule_sha256":digest,
        "model":"NOAA GFS 0.25deg 00Z operational","baseline":"NOAA 1991–2020 hourly normal",
        "events":planned,"future_observations_assessed":False,
        "independent_preregistration_confirmed":False,
        "source_registry_accepted":False,
        "scientific_admission":"HOLD",
    }
