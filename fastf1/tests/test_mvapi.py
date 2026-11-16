from fastf1 import get_session
from fastf1.mvapi import get_circuit_info
from fastf1.testing import (
    capture_log,
    run_in_subprocess
)


def test_get_circuit_info():
    circuit_info = get_circuit_info(year=2020, circuit_key=39)

    assert circuit_info is not None

    for col, dtype in (("X", 'float64'), ("Y", 'float64'), ("Number", 'int64'),
                       ("Letter", 'object'), ("Angle", 'float64'),
                       ("Distance", 'float64')):
        assert col in circuit_info.corners.columns
        assert circuit_info.corners.dtypes[col] == dtype


def test_get_circuit_info_warns_no_telemetry(caplog):
    session = get_session(2020, 'Italy', 'R')
    session.load(telemetry=False)

    session.get_circuit_info()

    assert "Failed to generate marker distance information" in caplog.text


def test_get_circuit_info_invalid_key():
    run_in_subprocess(_test_get_circuit_info,
                      patch_cache_error_responses=True)


def _test_get_circuit_info():
    # requires a subprocess to prevent the modification of cache settings from
    # influencing other tests; caching of the expected error response is
    # enabled through ``patch_cache_error_responses``
    log_handle = capture_log()

    get_circuit_info(year=2020, circuit_key=0)
    assert "Failed to load circuit info" in log_handle.text
