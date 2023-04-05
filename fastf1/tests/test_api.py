import datetime

import numpy as np
import pandas as pd

from fastf1 import Cache
import fastf1.api


def test_timing_data():
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/'
              '2020_05_FP2/timing_data.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1.api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    lap_data, stream_data = \
        fastf1.api.timing_data('api/path', response=response)

    # ########## verify lap data
    assert (isinstance(lap_data, pd.DataFrame)
            and isinstance(stream_data, pd.DataFrame))
    assert len(lap_data['Driver'].unique()) == 20  # 20 drivers
    assert len(lap_data.columns) == 18
    assert (lap_data.dtypes == [
        'timedelta64[ns]', 'object', 'timedelta64[ns]', 'int64', 'int64',
        'timedelta64[ns]', 'timedelta64[ns]', 'timedelta64[ns]',
        'timedelta64[ns]', 'timedelta64[ns]', 'timedelta64[ns]',
        'timedelta64[ns]', 'timedelta64[ns]', 'float64', 'float64',
        'float64', 'float64', 'bool']).all()

    # these columns should not contain any NA values
    assert not lap_data.isna().loc[:, ('Time', 'Driver', 'NumberOfLaps',
                                       'NumberOfPitStops')].any().any()
    # double .any(): 1st within column, 2nd column results combined

    # these columns need to contain same number of NA values (outlap)
    count1 = lap_data.isna().loc[:, 'Sector1Time'].sum()
    count2 = lap_data.isna().loc[:, 'Sector1SessionTime'].sum()
    assert count1 == count2
    assert count1 > 50

    # laps with no sector1time need to have a pit out time
    mask = lap_data.isna().loc[:, 'Sector1Time']
    assert not lap_data.loc[mask, 'PitOutTime'].isna().any()

    # sum of sector times needs to be equal to lap time
    mask = (~lap_data.isna().loc[:, ('Sector1Time', 'LapTime')]).all(axis=1)
    sums = lap_data.loc[mask, ('Sector1Time',
                               'Sector2Time',
                               'Sector3Time')].sum(axis=1)
    assert np.allclose(sums.to_numpy().astype(float),
                       lap_data.loc[mask, 'LapTime'].to_numpy().astype(float))

    # ########## verify stream data
    # columns are Time, Driver, Position, GapToLeader, IntervalToPositionAhead
    assert len(stream_data.columns) == 5
    assert (stream_data.dtypes == ['timedelta64[ns]', 'object', 'int64',
                                   'float64', 'float64']).all()
    assert not stream_data.loc[:, ('Time', 'Driver', 'Position')]\
        .isna().any().any()


def test_timing_app_data():
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/'
              '2020_05_FP2/timing_app_data.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1.api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1.api.timing_app_data('api/path', response=response)

    # ########## verify lap data
    assert isinstance(data, pd.DataFrame)
    assert len(data.columns) == 13
    assert (data.dtypes == [
        'float64', 'object', 'timedelta64[ns]', 'int64', 'float64',
        'object', 'bool', 'bool', 'timedelta64[ns]', 'float64',
        'object', 'float64', 'object']).all()


def test_car_data(caplog):
    with Cache.disabled():
        response = list()
        with open('fastf1/testing/reference_data/'
                  '2020_05_FP2/car_data.raw', 'rb') as fobj:
            for line in fobj.readlines():
                response.append(line.decode('utf-8-sig'))

        # parse data; api path is unused here so it does not need to be valid
        data = fastf1.api.car_data('api/path', response=response)
        assert "failed to decode" not in caplog.text
        assert isinstance(data, dict)
        assert len(data) == 36  # 20 drivers and some problem with the raw data
        assert list(data.values())[0].shape == (27897, 9)  # dataframe shape
        assert (list(data.values())[0].dtypes == [
            'timedelta64[ns]', 'datetime64[ns]', 'int64', 'int64', 'int64',
            'int64', 'bool', 'int64', 'object']).all()

        response = response[:50]  # use less samples to speed test up
        # truncate one response: missing data -> cannot be decoded
        response[10] = response[10][:20]
        # parse and verify that error message is logged
        data = fastf1.api.position_data('api/path', response=response)
        assert "failed to decode" in caplog.text


def test_position_data(caplog):
    with Cache.disabled():
        response = list()
        with open('fastf1/testing/reference_data/'
                  '2020_05_FP2/position.raw', 'rb') as fobj:
            for line in fobj.readlines():
                response.append(line.decode('utf-8-sig'))

        # parse data; api path is unused here so it does not need to be valid
        data = fastf1.api.position_data('api/path', response=response)
        assert "failed to decode" not in caplog.text
        assert isinstance(data, dict)
        assert len(data) == 20  # 20 drivers
        assert list(data.values())[0].shape == (26840, 7)  # dataframe shape
        assert (list(data.values())[0].dtypes == [
            'timedelta64[ns]', 'datetime64[ns]', 'object',
            'int64', 'int64', 'int64', 'object']).all()

        response = response[:50]  # use less samples to speed test up
        # truncate one response: missing data -> cannot be decoded
        response[10] = response[10][:20]
        # parse and verify that error message is logged
        data = fastf1.api.position_data('api/path', response=response)
        assert "failed to decode" in caplog.text


def test_track_status_data():
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/'
              '2020_05_FP2/track_status.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1.api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1.api.track_status_data('api/path', response=response)

    # ########## verify lap data
    assert isinstance(data, dict)
    assert len(data.keys()) == 3
    dtypes = [datetime.timedelta, str, str]
    for col, dtype in zip(data.values(), dtypes):
        assert isinstance(col[0], dtype)
        assert len(col) == 7


def test_session_status_data():
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/'
              '2020_05_FP2/session_status.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1.api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1.api.session_status_data('api/path', response=response)

    # ########## verify lap data
    assert isinstance(data, dict)
    assert len(data.keys()) == 2
    dtypes = [datetime.timedelta, str]
    for col, dtype in zip(data.values(), dtypes):
        assert isinstance(col[0], dtype)
        assert len(col) == 5


def test_weather_data():
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/'
              '2020_05_FP2/weather_data.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1.api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1.api.weather_data('api/path', response=response)

    # ########## verify lap data
    assert isinstance(data, dict)
    assert len(data.keys()) == 8
    dtypes = [
        datetime.timedelta, float, float, float, bool, float, int, float
    ]
    for col, dtype in zip(data.values(), dtypes):
        assert isinstance(col[0], dtype)
        assert len(col) == 100


def test_lap_count_data():
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/'
              '2021_01_R/lap_count.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1.api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1.api.lap_count('api/path', response=response)

    # ########## verify lap data
    assert isinstance(data, dict)
    assert len(data.keys()) == 3
    dtypes = [datetime.timedelta, int, int]
    for col, dtype in zip(data.values(), dtypes):
        assert isinstance(col[0], dtype)
        assert len(col) == 57


def test_driver_list():
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/'
              '2020_05_FP2/driver_list.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1.api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1.api.driver_info('api/path', response=response)

    # ########## verify driver data
    assert isinstance(data, dict)
    assert len(data.keys()) == 20
    dtypes = [str, str, str, str, int, str, str, str, str, str, str,
              datetime.timedelta, datetime.timedelta, datetime.timedelta,
              datetime.timedelta, str, float]
    for driver in data.values():
        for col, dtype in zip(driver.values(), dtypes):
            assert isinstance(col, dtype)
