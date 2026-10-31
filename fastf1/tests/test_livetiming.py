import os

from unittest.mock import patch

import fastf1.events
from fastf1.exceptions import F1AuthError
from fastf1.livetiming.data import LiveTimingData
from fastf1.livetiming.client import SignalRClient


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


def test_no_auth_omits_token_factory(tmpdir):
    # test that the access_token_factory is not set when no auth is used
    tmpfile = os.path.join(tmpdir, "tmpfile.txt")
    client = SignalRClient(tmpfile, no_auth=True)
    with patch("fastf1.livetiming.client.requests") as fake_requests, \
            patch("fastf1.livetiming.client.HubConnectionBuilder") as builder:
        fake_requests.options.return_value.cookies = {"AWSALBCORS": "x"}
        client._is_connected = True
        client._run()
        client._output_file.close()
        options = builder.return_value.with_url.call_args.kwargs["options"]
        assert "access_token_factory" not in options


def test_failed_login_omits_token_factory(tmpdir):
    tmpfile = os.path.join(tmpdir, "tmpfile.txt")
    client = SignalRClient(tmpfile)
    with patch("fastf1.livetiming.client.requests") as fake_requests, \
            patch("fastf1.livetiming.client.HubConnectionBuilder") as hub, \
            patch("fastf1.livetiming.client.get_token",
                    side_effect=F1AuthError("failed")):
        fake_requests.options.return_value.cookies = {"AWSALBCORS": "x"}
        client._is_connected = True
        client._run()
        client._output_file.close()
        options = hub.return_value.with_url.call_args.kwargs["options"]
        assert "access_token_factory" not in options


def test_login_passes_token_factory(tmpdir):
    tmpfile = os.path.join(tmpdir, "tmpfile.txt")
    client = SignalRClient(tmpfile)
    with patch("fastf1.livetiming.client.requests") as fake_requests, \
            patch("fastf1.livetiming.client.HubConnectionBuilder") as hub, \
            patch("fastf1.livetiming.client.get_token"):
        fake_requests.options.return_value.cookies = {"AWSALBCORS": "x"}
        client._is_connected = True
        client._run()
        client._output_file.close()
        options = hub.return_value.with_url.call_args.kwargs["options"]
        assert "access_token_factory" in options
