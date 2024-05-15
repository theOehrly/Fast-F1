import os

import fastf1.events
from fastf1.livetiming.data import LiveTimingData


def test_file_loading_w_errors():
    # load file with many errors and invalid data without crashing
    livedata = LiveTimingData('fastf1/testing/reference_data/livedata/with_errors.txt')
    livedata.load()


def test_file_loading():
    # load a valid file
    livedata = LiveTimingData('fastf1/testing/reference_data/livedata/2021_1_FP3.txt')
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
