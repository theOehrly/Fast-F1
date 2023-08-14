import requests_mock

from fastf1 import get_session
from fastf1.mvapi import get_circuit_info


def _setup_mocker(mocker):
    with open('fastf1/testing/reference_data/2020_05_FP2/mvapi_circuits.raw',
              'rb') as fobj:
        content = fobj.read()
    mocker.get('https://api.multiviewer.app/api/v1/circuits/39/2020',
               content=content, status_code=200)


def test_get_circuit_info():
    with requests_mock.Mocker() as mocker:
        _setup_mocker(mocker)
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

    with requests_mock.Mocker() as mocker:
        _setup_mocker(mocker)
        session.get_circuit_info()

    assert "Failed to generate marker distance information" in caplog.text


def test_get_circuit_info_invalid_key(caplog):
    get_circuit_info(year=2020, circuit_key=0)
    assert "Failed to load circuit info" in caplog.text
