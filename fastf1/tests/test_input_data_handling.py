# test some known special cases

import pytest

import logging

import pandas as pd

import fastf1
import fastf1.ergast
import fastf1.testing


@pytest.mark.f1telapi
@pytest.mark.skip(reason="required data not available")
def test_partial_position_data(caplog):
    # RUS is missing the first half of the position data because F1 somehow
    # switches from development driver to RUS mid-session
    # this requires recreating missing data (empty) so that the data has the correct size
    caplog.set_level(logging.INFO)

    session = fastf1.get_session(2020, 'Barcelona', 'FP2')
    session.load_laps()

    assert "Car data for driver 63 is incomplete!" in caplog.text  # the warning
    assert "Laps loaded and saved!" in caplog.text  # indicates success


@pytest.mark.f1telapi
@pytest.mark.skip(reason="required data not available")
def test_history_mod_1(caplog):
    # api data sometimes goes back in time
    caplog.set_level(logging.INFO)

    session = fastf1.get_session(2020, 'testing', 3)
    session.load_laps()

    assert "The api attempted to rewrite history" in caplog.text  # the warning
    assert "Laps loaded and saved!" in caplog.text  # indicates success


@pytest.mark.f1telapi
def test_ergast_lookup_fail():
    fastf1.testing.run_in_subprocess(_test_ergast_lookup_fail)


def _test_ergast_lookup_fail():
    fastf1.Cache.enable_cache('test_cache')
    log_handle = fastf1.testing.capture_log()

    # ergast lookup fails if data is requested to soon after a session ends

    def fail_load(*args, **kwargs):
        raise Exception
    fastf1.ergast.load = fail_load  # force function call to fail

    session = fastf1.get_session(2020, 3, 'FP2')  # rainy and short session, good for fast test/quick loading
    session.load_laps()

    assert "Failed to load data from Ergast API!" in log_handle.text  # the warning
    assert "Loaded data for" in log_handle.text  # indicates success


@pytest.mark.f1telapi
def test_crash_lap_added_1():
    # sainz crashed in his 14th lap, there need to be all 14 laps
    session = fastf1.get_session(2021, "Monza", 'FP2')

    laps = session.load_laps(with_telemetry=False)
    assert laps.pick_driver('SAI').shape[0] == 14


@pytest.mark.f1telapi
def test_crash_lap_added_2():
    # verstappen crashed on his first lap, the lap needs to exist
    session = fastf1.get_session(2021, 'British Grand Prix', 'R')

    laps = session.load_laps(with_telemetry=False)
    assert laps.pick_driver('VER').shape[0] == 1


@pytest.mark.f1telapi
def test_inlap_added():
    fastf1.testing.run_in_subprocess(_test_inlap_added)


def _test_inlap_added():
    # !! API parser test - require running without cache !!
    # perez aborted his last q3 run and went straight into the pits
    # lap data needs to be added so that telemetry can be loaded
    log_handle = fastf1.testing.capture_log(logging.WARNING)

    session = fastf1.get_session(2021, 'Mexico City', 'Q')

    laps = session.load_laps(with_telemetry=False)
    last = laps.pick_driver('PER').iloc[-1]
    assert not pd.isnull(last['PitInTime'])
    assert not pd.isnull(last['Time'])

    # verify that the test was actually run without caching enabled
    assert 'NO CACHE' in log_handle.text
