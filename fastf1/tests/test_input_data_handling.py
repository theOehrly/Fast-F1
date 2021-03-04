# test some known special cases

import pytest
import fastf1 as ff1
from fastf1 import core
import logging


@pytest.mark.f1telapi
@pytest.mark.skip(reason="required data not available")
def test_partial_position_data(caplog):
    ff1.Cache.enable_cache("test_cache/")
    # RUS is missing the first half of the position data because F1 somehow
    # switches from development driver to RUS mid-session
    # this requires recreating missing data (empty) so that the data has the correct size
    caplog.set_level(logging.INFO)

    session = core.get_session(2020, 'Barcelona', 'FP2')
    session.load_laps()

    assert "Car data for driver 63 is incomplete!" in caplog.text  # the warning
    assert "Laps loaded and saved!" in caplog.text  # indicates success


@pytest.mark.f1telapi
@pytest.mark.skip(reason="required data not available")
def test_history_mod_1(caplog):
    ff1.Cache.enable_cache("test_cache/")
    # api data sometimes goes back in time
    caplog.set_level(logging.INFO)

    session = core.get_session(2020, 'testing', 3)
    session.load_laps()

    assert "The api attempted to rewrite history" in caplog.text  # the warning
    assert "Laps loaded and saved!" in caplog.text  # indicates success


@pytest.mark.f1telapi
def test_ergast_lookup_fail(caplog):
    ff1.Cache.enable_cache("test_cache/")
    # ergast lookup fails if data is requested to soon after a session ends
    caplog.set_level(logging.INFO)

    def fail_load(*args, **kwargs):
        raise Exception
    core.ergast.load = fail_load  # force function call to fail

    session = core.get_session(2020, 3, 'FP2')  # rainy and short session, good for fast test/quick loading
    session.load_laps()

    assert "Failed to load data from Ergast API!" in caplog.text  # the warning
    assert "Loaded data for" in caplog.text  # indicates success
