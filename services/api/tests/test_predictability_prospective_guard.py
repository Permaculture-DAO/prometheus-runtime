"""Synthetic-only checks of frozen future NOAA issue universe and receipt chronology.

Never treats a claimed local timestamp as independent evidence or code PASS as
scientific/source approval. No network calls or live weather.
"""
from datetime import datetime,timedelta,timezone
import pytest
from pydantic import ValidationError
from app.predictability_prospective_guard import (
    PROTOCOL_ID,WINDOW_START,WINDOW_END_EXCLUSIVE,
    CaptureReceipt,ProspectiveEvent,prospective_schedule,screen_event,
)

UTC=timezone.utc

def dt(day=20,hour=0,minutes=0):
    return datetime(2026,10,day,hour,minutes,tzinfo=UTC)

def receipt(url,day=20,hour=4):
    return CaptureReceipt(
        source_url=url,file_sha256="a"*64,
        first_seen_utc=dt(day,hour),local_receipt_id=f"LOCAL-{day}-{hour}",
    )

MODEL="https://noaa-gfs-bdp-pds.s3.amazonaws.com/gfs.20261020/00/atmos/gfs.t00z.pgrb2.0p25.f024"
STATION="https://noaa-ghcnh-pds.s3.amazonaws.com/hourly/access/by-year/2026/psv/station.psv"

def case():
    return ProspectiveEvent(
        protocol_id=PROTOCOL_ID,model_id="NOAA_GFS_0p25",site_id="USW00012839",
        issue_time=dt(),valid_time=dt(21),lead_hours=24,
        model_field=receipt(MODEL),model_index=receipt(MODEL+".idx"),
        station_observation=receipt(STATION,22,4),
        station_observed_at=dt(21,0),
        normal_file_sha256="b"*64,
    )

def test_schedule_frozen_not_hindsight_selected():
    a=prospective_schedule()
    assert a==prospective_schedule()
    assert a["issue_days"]==92
    assert a["planned_events"]==828
    assert a["events"][0]["issue_time"].startswith("2026-10-20")
    assert a["events"][-1]["issue_time"].startswith("2027-01-19")
    assert not a["independent_preregistration_confirmed"]
    assert a["scientific_admission"]=="HOLD"

def test_local_receipts_not_treated_as_certification():
    out=screen_event(case())
    assert out["status"]=="LOCAL_CHRONOLOGY_PLAUSIBLE_UNVERIFIED"
    assert out["failure_codes"]==[]
    assert not out["forecast_source_authenticity_verified"]
    assert not out["first_seen_time_independently_attested"]
    assert out["validated_horizon_hours"] is None
    assert out["land_capital_insurance_authority"] is False

def test_missing_target_observation_does_not_pass():
    example=case()
    example.station_observation=None
    example.station_observed_at=None
    result=screen_event(example)
    assert result["status"]=="HOLD_OBSERVATION_NOT_AVAILABLE"

@pytest.mark.parametrize("change,expected",[
    ({"protocol_id":"WRONG"},"PROTOCOL_ID_MISMATCH"),
    ({"site_id":"MISSING"},"STATION_OUTSIDE_FROZEN_UNIVERSE"),
    ({"model_id":"NOT_NOAA"},"MODEL_OUTSIDE_PROTOCOL"),
    ({"lead_hours":12},"LEAD_OUTSIDE_FROZEN_UNIVERSE"),
    ({"issue_time":dt(19)},"ISSUE_OUTSIDE_FROZEN_WINDOW"),
    ({"issue_time":dt(20,6)},"NOT_00Z_ISSUE"),
    ({"valid_time":dt(22)},"TARGET_LEAD_MISMATCH"),
])
def test_outside_contract_fails(change,expected):
    item=case().model_copy(update=change)
    result=screen_event(item)
    assert result["status"]=="HOLD_INVALID_LOCAL_CHRONOLOGY"
    assert expected in result["failure_codes"]

def test_future_capture_or_wrong_source_fails():
    item=case()
    item.model_field=receipt(MODEL,21,1)
    item.model_index=receipt("https://example.org/false.idx")
    out=screen_event(item)
    assert "MODEL_CAPTURE_AFTER_FORECAST_VALIDITY" in out["failure_codes"]
    assert "GFS_INDEX_NOT_FROZEN_PRODUCT" in out["failure_codes"]

def test_stale_issue_source_before_run_fails():
    item=case()
    item.model_field=receipt(MODEL,19,23)
    out=screen_event(item)
    assert "SOURCE_FIRST_SEEN_BEFORE_NOMINAL_INIT" in out["failure_codes"]

def test_station_measurement_not_yet_occurred_fails():
    item=case()
    item.station_observation=receipt(STATION,20,4)
    out=screen_event(item)
    assert "OBS_CAPTURE_BEFORE_MEASUREMENT" in out["failure_codes"]

def test_baseline_must_be_climate_normal_for_primary():
    item=case()
    item.baseline_kind="PERSISTENCE"
    assert "PRIMARY_BASELINE_MUST_BE_CLIMATE_NORMAL" in screen_event(item)["failure_codes"]

def test_no_persistence_promotion_without_preissue_snapshot():
    item=case()
    item.persistence_observed_at=dt(19,23)
    item.persistence_snapshot=receipt(STATION,20,4)
    result=screen_event(item)
    assert not result["local_persistence_chronology_plausible"]
    assert "PERSISTENCE_SNAPSHOT_NOT_CAPTURED_BEFORE_ISSUE" in result["failure_codes"]

def test_preissue_persistence_is_only_unattested_local_plausibility():
    item=case()
    item.persistence_observed_at=dt(19,22)
    item.persistence_snapshot=receipt(STATION,19,23)
    result=screen_event(item)
    assert result["local_persistence_chronology_plausible"]
    assert not result["first_seen_time_independently_attested"]

def test_timezone_naive_capture_is_rejected():
    with pytest.raises(ValidationError):
        CaptureReceipt(source_url=MODEL,file_sha256="a"*64,
                       first_seen_utc=datetime(2026,10,20,4),local_receipt_id="bad")

def test_outside_future_limit():
    item=case()
    item.issue_time=WINDOW_END_EXCLUSIVE
    assert "ISSUE_OUTSIDE_FROZEN_WINDOW" in screen_event(item)["failure_codes"]

def test_no_extra_controls_accepted_by_schema():
    data=case().model_dump(mode="json")
    data["approved_by_scientist"]=True
    with pytest.raises(ValidationError):
        ProspectiveEvent.model_validate(data)

def test_correct_bucket_wrong_lead_is_rejected():
    item=case()
    incorrect=MODEL.replace("f024", "f048")
    item.model_field=receipt(incorrect)
    result=screen_event(item)
    assert result["status"]=="HOLD_INVALID_LOCAL_CHRONOLOGY"
    assert "GFS_FIELD_NOT_FROZEN_PRODUCT" in result["failure_codes"]

def test_correct_bucket_wrong_date_is_rejected():
    item=case()
    item.model_index=receipt(MODEL.replace("20261020", "20261021")+".idx")
    result=screen_event(item)
    assert "GFS_INDEX_NOT_FROZEN_PRODUCT" in result["failure_codes"]
