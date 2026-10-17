"""Synthetic, fully offline tests of NOAA byte- and chronology-bound receipt preparation."""
from datetime import datetime, timezone, timedelta

import pytest

from app.predictability_capture_receipt import (
    create_local_capture_receipt,
    frozen_model_url,
    select_noaa_temperature_range,
)

UTC = timezone.utc
ISSUE = datetime(2026,10,20,tzinfo=UTC)
DATA = b"GRIB" + b"abcd" + b"7777"
INDEX = (
    b"1:0:d=2026102000:PRMSL:mean sea level:24 hour fcst:\n"
    b"2:100:d=2026102000:TMP:2 m above ground:24 hour fcst:\n"
    b"3:112:d=2026102000:RH:2 m above ground:24 hour fcst:\n"
)


def valid_kwargs():
    return dict(
        issue_time=ISSUE,lead_hours=24,index_bytes=INDEX,grib_bytes=DATA,
        grib_response_status=206,grib_content_range="bytes 100-111/999",
        index_response_status=200,
        index_response_headers={"Date":"Tue, 20 Oct 2026 04:00:00 GMT",
                               "ETag":'"not-a-signature"'},
        grib_response_headers={"Date":"Tue, 20 Oct 2026 04:00:00 GMT",
                               "Content-Range":"bytes 100-111/999"},
        first_seen_utc=ISSUE+timedelta(hours=4),
    )


def test_schedule_index_url_and_hash_receipts():
    assert frozen_model_url(ISSUE,24).endswith("gfs.t00z.pgrb2.0p25.f024")
    assert select_noaa_temperature_range(INDEX,ISSUE,24)==(100,111)
    a=create_local_capture_receipt(**valid_kwargs())
    assert a==create_local_capture_receipt(**valid_kwargs())
    assert a["grib_index_range"]==[100,111]
    assert len(a["model_field_sha256"])==64
    assert not a["source_publication_time_attested"]
    assert not a["prospective_scientific_event_certified"]
    assert not a["source_registry_admitted"]
    assert not a["land_credit_insurance_authority"]
    assert a["capture_classification"]=="LOCAL_CANDIDATE_UNATTESTED_NOT_ADMITTED"


@pytest.mark.parametrize("field,replacement,pattern", [
    ("grib_response_status",200,"HTTP 206"),
    ("grib_content_range","bytes 100-111/777","smaller than indexed"), # corrected below
    ("index_response_status",404,"HTTP 200"),
    ("grib_bytes",b"GRIBxxxxBAD!", "invalid standalone"),
    ("grib_bytes",b"GRIB7777","content length"),
    ("first_seen_utc",ISSUE-timedelta(minutes=1),"outside nominal"),
    ("first_seen_utc",ISSUE+timedelta(hours=13),"outside nominal"),
    ("first_seen_utc",ISSUE+timedelta(hours=25),"outside nominal"),
])
def test_invalid_file_or_receipt_data_rejected(field,replacement,pattern):
    kw=valid_kwargs()
    kw[field]=replacement
    if field=="grib_content_range":
        kw[field]="bytes 100-111/100"
    with pytest.raises(ValueError,match=pattern):
        create_local_capture_receipt(**kw)


def test_wrong_http_range_fails():
    kw=valid_kwargs()
    kw["grib_content_range"]="bytes 101-112/999"
    with pytest.raises(ValueError,match="does not match"):
        create_local_capture_receipt(**kw)


def test_future_file_name_outside_frozen_cohort():
    with pytest.raises(ValueError,match="outside preregistered"):
        frozen_model_url(datetime(2026,10,19,tzinfo=UTC),24)


def test_lead_mismatch_or_duplicated_target_field_fails():
    with pytest.raises(ValueError,match="exactly one"):
        select_noaa_temperature_range(INDEX,ISSUE,48)
    duplicate=INDEX.replace(b"3:112:d=2026102000:RH",
                            b"3:112:d=2026102000:TMP")
    with pytest.raises(ValueError,match="exactly one"):
        select_noaa_temperature_range(duplicate,ISSUE,24)


def test_unsafe_index_offset_order_fails():
    malformed=INDEX.replace(b"3:112:d=",b"3:98:d=")
    with pytest.raises(ValueError,match="non-increasing"):
        select_noaa_temperature_range(malformed,ISSUE,24)


def test_wrong_issue_field_rejected():
    tampered=INDEX.replace(b"d=2026102000:TMP",b"d=2026102100:TMP")
    with pytest.raises(ValueError,match="incorrect issued-at"):
        select_noaa_temperature_range(tampered,ISSUE,24)


def test_no_time_zone_rejected():
    with pytest.raises(ValueError,match="timezone aware"):
        frozen_model_url(datetime(2026,10,20,0),24)


def test_bytes_not_caller_hash_are_hashed():
    receipt=create_local_capture_receipt(**valid_kwargs())
    assert receipt["model_index_sha256"] != receipt["model_field_sha256"]
