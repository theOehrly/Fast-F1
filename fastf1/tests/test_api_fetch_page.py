"""Offline tests for ``fastf1._api.fetch_page`` (no API access required).

The HTTP request is replaced by a mocked response, so these tests only
verify the splitting of jsonStream records into timestamp and payload.
"""
import json

import pytest

import fastf1._api
from fastf1._api import fetch_page


class _MockResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code


def _mock_stream(monkeypatch, records, status_code=200, bom=True):
    raw = "".join(r + "\r\n" for r in records)
    content = raw.encode("utf-8-sig" if bom else "utf-8")

    def _requests_get(urls, **kwargs):
        return _MockResponse(content, status_code)

    monkeypatch.setattr(fastf1._api.Cache, "requests_get", _requests_get)


MSG_STANDARD = (
    '{"Messages":{"5":{"Utc":"2026-10-31T17:42:56","Category":"Flag",'
    '"Flag":"CLEAR","Scope":"Sector","Sector":2,'
    '"Message":"CLEAR IN TRACK SECTOR 2"}}}'
)
MSG_LIST = (
    '{"Messages":[{"Utc":"2026-10-31T17:36:46","Category":"Other",'
    '"Message":"CAR 10 (GAS) LAP DELETED - TRACK LIMITS AT TURN 12 '
    'LAP 2 11:35:28"},{"Utc":"2026-11-01T19:20:00","Lap":1,'
    '"Category":"Flag","Flag":"GREEN","Scope":"Track",'
    '"Message":"GREEN LIGHT - PIT EXIT OPEN"}]}'
)


@pytest.mark.parametrize(
    "record, expected_ts, payload",
    [
        # standard format HH:MM:SS.mmm
        ("00:20:22.286" + MSG_STANDARD, "00:20:22.286", MSG_STANDARD),
        ("23:59:59.999" + MSG_LIST, "23:59:59.999", MSG_LIST),
        # format D.HH:MM:SS.mmm, day prefix is discarded
        ("1.01:57:26.903" + MSG_LIST, "01:57:26.903", MSG_LIST),
        # format DD.HH:MM:SS.mmm, day prefix is discarded
        ("12.01:57:26.903" + MSG_STANDARD, "01:57:26.903", MSG_STANDARD),
        # payload containing '.' and ':' must not affect splitting
        ('1.00:00:00.000{"A":"1.01:57:26.903"}', "00:00:00.000",
         '{"A":"1.01:57:26.903"}'),
        ('00:00:00.000{"A":"1.01:57:26.903"}', "00:00:00.000",
         '{"A":"1.01:57:26.903"}'),
        # minimal payload
        ("00:00:00.000{}", "00:00:00.000", "{}"),
        ("3.00:00:00.000{}", "00:00:00.000", "{}"),
    ]
)
def test_fetch_page_timestamp_formats(monkeypatch, record, expected_ts,
                                      payload):
    _mock_stream(monkeypatch, [record])
    ret = fetch_page("dummy/path/", "race_control_messages")
    assert ret == [[expected_ts, json.loads(payload)]]


def test_fetch_page_mixed_timestamp_formats(monkeypatch):
    # timestamp format may change from record to record
    records = [
        "00:20:22.286" + MSG_STANDARD,
        "1.01:57:26.903" + MSG_LIST,
        "00:20:23.000" + MSG_STANDARD,
        "12.23:59:59.999" + MSG_LIST,
        "1.00:00:00.001" + MSG_STANDARD,
    ]
    _mock_stream(monkeypatch, records)
    ret = fetch_page("dummy/path/", "race_control_messages")

    assert [r[0] for r in ret] == [
        "00:20:22.286",
        "01:57:26.903",
        "00:20:23.000",
        "23:59:59.999",
        "00:00:00.001",
    ]
    assert [r[1] for r in ret] == [
        json.loads(MSG_STANDARD),
        json.loads(MSG_LIST),
        json.loads(MSG_STANDARD),
        json.loads(MSG_LIST),
        json.loads(MSG_STANDARD),
    ]
    for ts, _ in ret:
        assert len(ts) == 12


def test_fetch_page_without_bom(monkeypatch):
    _mock_stream(monkeypatch,
                 ["00:20:22.286" + MSG_STANDARD, "1.01:57:26.903" + MSG_LIST],
                 bom=False)
    ret = fetch_page("dummy/path/", "race_control_messages")
    assert ret == [["00:20:22.286", json.loads(MSG_STANDARD)],
                   ["01:57:26.903", json.loads(MSG_LIST)]]


def test_fetch_page_decode_error_mixed_formats(monkeypatch, caplog):
    # broken records are skipped for both formats, valid ones are kept
    records = [
        "00:20:22.286" + MSG_STANDARD,
        '00:20:22.500{"broken": ',
        '1.01:57:26.903{"broken": ',
        "1.01:57:27.000" + MSG_LIST,
    ]
    _mock_stream(monkeypatch, records)
    with caplog.at_level("WARNING"):
        ret = fetch_page("dummy/path/", "race_control_messages")

    assert ret == [["00:20:22.286", json.loads(MSG_STANDARD)],
                   ["01:57:27.000", json.loads(MSG_LIST)]]
    assert "Failed to decode 2 messages (4 messages total)" in caplog.text


@pytest.mark.parametrize("name", ["position", "car_data"])
def test_fetch_page_raw_records_unchanged(monkeypatch, name):
    # position and car_data return unsplit raw records (memory efficiency)
    records = ['00:20:22.286"7ZXBattrb"', '1.01:57:26.903"7ZXBattrb"']
    _mock_stream(monkeypatch, records)
    assert fetch_page("dummy/path/", name) == records


def test_fetch_page_request_failed(monkeypatch):
    _mock_stream(monkeypatch, ["00:20:22.286" + MSG_STANDARD],
                 status_code=404)
    assert fetch_page("dummy/path/", "race_control_messages") is None
