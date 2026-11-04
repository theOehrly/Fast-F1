import os
from unittest.mock import patch

import fastf1.events
from fastf1.exceptions import F1AuthError
from fastf1.livetiming.client import SignalRClient
from fastf1.livetiming.data import LiveTimingData


def test_file_loading_w_errors():
    # load file with many errors and invalid data without crashing
    livedata = LiveTimingData('fastf1/testing/data/livedata/with_errors.txt')
    livedata.load()


def test_file_loading():
    # load a valid file
    livedata = LiveTimingData('fastf1/testing/data/livedata/2021_1_FP3.txt')
    livedata.load()

    session = fastf1.get_session(2021, 1, 'Practice 3')
    session.load(livedata=livedata)

    assert session.laps.shape == (273, 31)
    assert session.car_data['44'].shape == (17362, 10)


def test_duplicate_removal(tmpdir):
    # create a temporary file with two identical lines of data
    tmpfile = os.path.join(tmpdir, 'tmpfile.txt')
    tmpfile2 = os.path.join(tmpdir, 'tmpfile2.txt')

    data = "['TimingAppData', {'Lines': {'22': {'Stints': {'0': {" \
           "'LapFlags': 0, 'Compound': 'UNKNOWN', 'New': 'false'," \
           "'TyresNotChanged': '0', 'TotalLaps': 0, 'StartLaps':" \
           "0}}}}}, '2021-03-27T12:00:32.086Z']\n"

    with open(tmpfile, 'w') as fobj:
        fobj.write(data)

    with open(tmpfile2, 'w') as fobj:
        fobj.write(data)

    livedata = LiveTimingData(tmpfile, tmpfile2)
    assert len(livedata.get('TimingAppData')) == 1


def _get_connection_options(client):
    with patch("fastf1.livetiming.client.requests"), \
            patch("fastf1.livetiming.client.HubConnectionBuilder") as hub:
        client._is_connected = True  # the mocked connection never opens
        client._run()
    client._output_file.close()
    return hub.return_value.with_url.call_args.kwargs["options"]


def test_no_auth_omits_token_factory(tmpdir):
    client = SignalRClient(os.path.join(tmpdir, "tmpfile.txt"), no_auth=True)
    assert "access_token_factory" not in _get_connection_options(client)


def test_failed_login_omits_token_factory(tmpdir):
    client = SignalRClient(os.path.join(tmpdir, "tmpfile.txt"))
    with patch("fastf1.livetiming.client.get_token",
               side_effect=F1AuthError("failed")):
        assert "access_token_factory" not in _get_connection_options(client)


def test_login_passes_token_factory(tmpdir):
    client = SignalRClient(os.path.join(tmpdir, "tmpfile.txt"))
    with patch("fastf1.livetiming.client.get_token"):
        assert "access_token_factory" in _get_connection_options(client)
