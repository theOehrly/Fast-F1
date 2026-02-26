import datetime
import logging

import numpy as np
import pandas as pd
import pytest

import fastf1._api
from fastf1 import Cache


def test_timing_data():
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/'
              '2020_05_FP2/timing_data.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1._api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    lap_data, stream_data = \
        fastf1._api.timing_data('api/path', response=response)

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
            response.append([dec[:tl], fastf1._api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1._api.timing_app_data('api/path', response=response)

    # ########## verify lap data
    assert isinstance(data, pd.DataFrame)
    assert len(data.columns) == 13
    assert (data.dtypes == [
        'float64', 'object', 'timedelta64[ns]', 'int64', 'float64',
        'object', 'object', 'object', 'timedelta64[ns]', 'float64',
        'object', 'float64', 'object']).all()


def test_car_data(caplog):
    with Cache.disabled():
        response = list()
        with open('fastf1/testing/reference_data/'
                  '2020_05_FP2/car_data.raw', 'rb') as fobj:
            for line in fobj.readlines():
                response.append(line.decode('utf-8-sig'))

        # parse data; api path is unused here so it does not need to be valid
        data = fastf1._api.car_data('api/path', response=response)
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
        data = fastf1._api.position_data('api/path', response=response)
        assert "failed to decode" in caplog.text


def test_position_data(caplog):
    with Cache.disabled():
        response = list()
        with open('fastf1/testing/reference_data/'
                  '2020_05_FP2/position.raw', 'rb') as fobj:
            for line in fobj.readlines():
                response.append(line.decode('utf-8-sig'))

        # parse data; api path is unused here so it does not need to be valid
        data = fastf1._api.position_data('api/path', response=response)
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
        data = fastf1._api.position_data('api/path', response=response)
        assert "failed to decode" in caplog.text


def test_track_status_data():
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/'
              '2020_05_FP2/track_status.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1._api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1._api.track_status_data('api/path', response=response)

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
            response.append([dec[:tl], fastf1._api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1._api.session_status_data('api/path', response=response)

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
            response.append([dec[:tl], fastf1._api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1._api.weather_data('api/path', response=response)

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
            response.append([dec[:tl], fastf1._api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1._api.lap_count('api/path', response=response)

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
              '2023_01_FP1/driver_list.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1._api.parse(dec[tl:])])

    # parse data; api path is unused here so it does not need to be valid
    data = fastf1._api.driver_info('api/path', response=response)

    # ########## verify driver data
    assert isinstance(data, dict)
    assert len(data.keys()) == 20  # 20 drivers in this GP
    dtypes = {'RacingNumber': str, 'BroadcastName': str, 'FullName': str,
              'Tla': str, 'Line': int, 'TeamName': str, 'TeamColour': str,
              'FirstName': str, 'LastName': str, 'Reference': str,
              'HeadshotUrl': str, 'CountryCode': str}
    for driver in data.values():
        assert len(driver.keys()) == 12  # 12 fields in each driver's info.
        for key, val in driver.items():
            assert isinstance(val, dtypes[key])

# ########## special test cases ##########

def test_timing_app_data_list_format_stints():
    """Test that list-format Stints (used in 2018-2020 API) are parsed correctly.

    In the 2018-2020 API format, the ``Stints`` field is sent as a list
    containing ALL stints every time a tyre update is sent. The old code
    would emit one row for EACH element in the list at the message
    timestamp, causing ``__fix_tyre_info`` to misassign stints when two
    different stints land at the same time.

    The fix (GH#841) emits only the last (highest-index) element of each
    list-format message, since earlier elements are historical
    re-broadcasts.  This matches the modern dict format's behavior of
    sending only the currently-updated stint per message.
    """
    # Simulate 2018-2020 API list-format: Driver 1 starts on SOFT (stint 0),
    # pits to MEDIUM (stint 1).
    response = [
        # T=1min: start of race - only 1 stint in the list
        ['1:00.000', {'Lines': {'1': {'Stints': [
            {'Compound': 'SOFT', 'New': 'true', 'StartLaps': 0}
        ]}}}],
        # T=20min: mid-race update - still on stint 0, resends the full list
        ['20:00.000', {'Lines': {'1': {'Stints': [
            {'Compound': 'SOFT', 'New': 'true', 'StartLaps': 0, 'TotalLaps': 19}
        ]}}}],
        # T=30min: pit stop - list now contains BOTH stints
        ['30:00.000', {'Lines': {'1': {'Stints': [
            {'Compound': 'SOFT', 'New': 'true', 'StartLaps': 0, 'TotalLaps': 20},
            {'Compound': 'MEDIUM', 'New': 'false', 'StartLaps': 0}
        ]}}}],
        # T=40min: after pit stop - both stints resent again
        ['40:00.000', {'Lines': {'1': {'Stints': [
            {'Compound': 'SOFT', 'New': 'true', 'StartLaps': 0, 'TotalLaps': 20},
            {'Compound': 'MEDIUM', 'New': 'false', 'StartLaps': 0, 'TotalLaps': 10}
        ]}}}],
    ]

    data = fastf1._api.timing_app_data('api/path', response=response)
    drv1 = data[data['Driver'] == '1']

    # With the new fix, each list message emits exactly one row (the last
    # element).  So we expect 4 rows total:
    #   T=1min  -> stint 0 (SOFT)     [last of 1-element list]
    #   T=20min -> stint 0 (SOFT)     [last of 1-element list]
    #   T=30min -> stint 1 (MEDIUM)   [last of 2-element list]
    #   T=40min -> stint 1 (MEDIUM)   [last of 2-element list]
    assert len(drv1) == 4, (
        f"Expected 4 rows (one per message), got {len(drv1)}."
    )

    # Critical invariant: no two *different* stints share the same timestamp
    for ts in drv1['Time'].unique():
        stints_at_ts = drv1.loc[drv1['Time'] == ts, 'Stint'].unique()
        assert len(stints_at_ts) == 1, (
            f"Multiple different stints at timestamp {ts}: {stints_at_ts}. "
            "This would trigger the __fix_tyre_info misassignment bug."
        )

    # First appearance timestamps are correct
    stints = drv1.drop_duplicates(subset='Stint').sort_values('Stint').reset_index(drop=True)
    assert stints.loc[0, 'Stint'] == 0
    assert stints.loc[0, 'Compound'] == 'SOFT'
    assert stints.loc[0, 'Time'] == pd.Timedelta(minutes=1)
    assert stints.loc[1, 'Stint'] == 1
    assert stints.loc[1, 'Compound'] == 'MEDIUM'
    assert stints.loc[1, 'Time'] == pd.Timedelta(minutes=30)


def test_timing_app_data_list_format_multi_element_same_timestamp():
    """Regression: multi-element list must NOT emit multiple stints at once.

    This covers the exact scenario from the 2018 Azerbaijan GP where five
    drivers received a 2-element list at the same timestamp.  The old
    code emitted *both* stints at that timestamp, which confused
    ``__fix_tyre_info`` into merging them.
    """
    # Single message with a 2-element list (mirrors the real API data)
    response = [
        ['13:19.945', {'Lines': {'7': {'Stints': [
            {'Compound': 'ULTRASOFT', 'New': 'false', 'TotalLaps': 4,
             'StartLaps': 3, 'TyresNotChanged': '0'},
            {'Compound': 'SOFT', 'New': 'true', 'TotalLaps': 0,
             'StartLaps': 0, 'TyresNotChanged': '0'}
        ]}}}],
    ]

    data = fastf1._api.timing_app_data('api/path', response=response)
    drv = data[data['Driver'] == '7']

    # Only the LAST element (stint 1 / SOFT) should be emitted
    assert len(drv) == 1, (
        f"Expected 1 row (only last element), got {len(drv)}."
    )
    assert drv.iloc[0]['Stint'] == 1
    assert drv.iloc[0]['Compound'] == 'SOFT'


def test_driver_list_contains_support_race(caplog):
    caplog.set_level(logging.WARNING)
    response = list()
    tl = 12  # length of timestamp: len('00:00:00:000')
    with open('fastf1/testing/reference_data/2023_11_FP1/driver_list.raw', 'rb') as fobj:
        for line in fobj.readlines():
            dec = line.decode('utf-8-sig')
            response.append([dec[:tl], fastf1._api.parse(dec[tl:])])

    # parse data; api path is unused here, so it does not need to be valid
    data = fastf1._api.driver_info('api/path', response=response)
    assert len(caplog.record_tuples) == 1
    _, _, warn_message = caplog.record_tuples[0]
    assert warn_message.startswith("Skipping delayed declaration of driver")

@pytest.mark.f1telapi
def test_deleted_laps_not_marked_personal_best():
    # see issue #165
    session = fastf1.get_session(2022, 'Spain', 'Q')
    laps_data, _ = fastf1._api.timing_data(session.api_path)
    nor = laps_data[laps_data['Driver'] == '4']  # get NOR laps

    # second to last lap was deleted, ensure it is not marked personal best
    assert (nor['IsPersonalBest']
            == [False, True, False, False, False, False,
                False, True, False, False, False, False]).all()


@pytest.mark.f1telapi
def test_personal_best_q_session_handled_individually():
    session = fastf1.get_session(2023, 'Canada', 'Q')
    laps_data, _ = fastf1._api.timing_data(session.api_path)
    ver = laps_data[laps_data['Driver'] == '1']  # get VER laps

    # Over all three Quali sessions, a total of 9 laps should be marked
    # as personal best. Quali was rainy with laps in Q2 and Q3 being slower.
    # If Quali session are not handled correctly individually, those laps are
    # not marked as personal best. (see issue #403)
    assert sum(ver['IsPersonalBest']) == 9
