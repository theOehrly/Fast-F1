# test some known special cases

import pytest

import logging

import pandas as pd

import fastf1
import fastf1.ergast
import fastf1.testing
from fastf1.testing.reference_values import LAP_DTYPES


@pytest.mark.f1telapi
def test_ergast_lookup_fail():
    fastf1.testing.run_in_subprocess(_test_ergast_lookup_fail)


def _test_ergast_lookup_fail():
    from fastf1.logger import LoggingManager
    LoggingManager.debug = False
    # special, relevant on Linux only.
    # debug=True does not propagate to subprocess on windows

    fastf1.Cache.enable_cache('test_cache')
    log_handle = fastf1.testing.capture_log()

    # ergast lookup fails if data is requested to soon after a session ends

    def fail_load(*args, **kwargs):
        raise Exception

    fastf1.ergast.Ergast._get = fail_load  # force function call to fail

    # rainy and short session, good for fast test/quick loading
    session = fastf1.get_session(2020, 3, 'FP2')
    session.load(telemetry=False, weather=False)

    # ensure that a warning is shown but overall data loading finishes
    assert "Failed to load result data from Ergast!" in log_handle.text
    assert "Finished loading data" in log_handle.text


@pytest.mark.f1telapi
def test_crash_lap_added_1():
    # sainz crashed in his 14th lap, there need to be all 14 laps
    session = fastf1.get_session(2021, "Monza", 'FP2')

    session.load(telemetry=False)
    assert session.laps.pick_driver('SAI').shape[0] == 14


@pytest.mark.f1telapi
def test_crash_lap_added_2():
    # verstappen crashed on his first lap, the lap needs to exist
    session = fastf1.get_session(2021, 'British Grand Prix', 'R')

    session.load(telemetry=False)
    assert session.laps.pick_driver('VER').shape[0] == 1


@pytest.mark.f1telapi
def test_no_extra_lap_if_race_not_started():
    # tsunoda had a technical issue shortly before the race and could not
    # start even though he is listed in the drivers list
    session = fastf1.get_session(2022, 2, 'R')

    session.load(telemetry=False, weather=False)
    assert session.laps.size
    assert session.laps.pick_driver('TSU').size == 0


@pytest.mark.f1telapi
def test_no_timing_app_data():
    fastf1.testing.run_in_subprocess(_test_no_timing_app_data)


def _test_no_timing_app_data():
    # subprocess test because api parser function is overwritten
    log_handle = fastf1.testing.capture_log(logging.WARNING)

    def _mock(*args, **kwargs):
        return pd.DataFrame(
            {'LapNumber': [], 'Driver': [], 'LapTime': [], 'Stint': [],
             'TotalLaps': [], 'Compound': [], 'New': [],
             'TyresNotChanged': [], 'Time': [], 'LapFlags': [],
             'LapCountTime': [], 'StartLaps': [], 'Outlap': []}
        )

    fastf1.api.timing_app_data = _mock

    session = fastf1.get_session(2020, 'Italy', 'R')
    with fastf1.Cache.disabled():
        session.load(telemetry=False, weather=False)

    assert 'Failed to load lap data!' not in log_handle.text
    assert 'No tyre data for driver' in log_handle.text

    assert session.laps.size
    assert all([col in session.laps.columns for col in LAP_DTYPES.keys()])


@pytest.mark.f1telapi
def test_inlap_added():
    session = fastf1.get_session(2021, 'Mexico City', 'Q')

    with fastf1.Cache.disabled():
        session.load(telemetry=False)

    last = session.laps.pick_driver('PER').iloc[-1]
    assert not pd.isnull(last['PitInTime'])
    assert not pd.isnull(last['Time'])


@pytest.mark.f1telapi
def test_lap_start_time_after_red_flag():
    # see GH#167
    session = fastf1.get_session(2022, 'Saudi Arabia', 'Q')
    session.load(telemetry=False, weather=False, messages=False)

    restart_time = pd.to_timedelta('01:54:24.197000')

    # ensure that verstappens first lap after the restart was also started
    # after the restart
    ver_laps = session.laps.pick_driver('VER')
    idx = ver_laps[(ver_laps['Time'] > restart_time)
                   & pd.notna(ver_laps['Time'])].index[0]
    assert ver_laps.loc[idx]['LapStartTime'] > restart_time


@pytest.mark.f1telapi
def test_partial_lap_retired_added():
    # test that a last (partial) lap is added for drivers that retire on track
    session = fastf1.get_session(2022, 1, 'R')
    session.load()

    assert session.laps.pick_driver('11').iloc[-1]['FastF1Generated']


@pytest.mark.f1telapi
def test_first_lap_time_added_from_ergast_in_race():
    session = fastf1.get_session(2022, 1, 'R')
    session.load(telemetry=False)

    assert not pd.isna(session.laps.pick_lap(1)['LapTime']).any()
