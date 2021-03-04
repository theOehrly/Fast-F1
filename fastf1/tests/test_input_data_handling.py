# test some known special cases

import pytest
from fastf1 import core
import logging


@pytest.mark.f1telapi
def test_partial_position_data(caplog):
    # RUS is missing the first half of the position data because F1 somehow
    # switches from development driver to RUS mid-session
    # this requires recreating missing data (empty) so that the data has the correct size
    caplog.set_level(logging.INFO)

    session = core.get_session(2020, 'Barcelona', 'FP2')
    session.load_laps()

    assert "Car data for driver 63 is incomplete!" in caplog.text  # the warning
    assert "Laps loaded and saved!" in caplog.text  # indicates success


@pytest.mark.f1telapi
def test_history_mod_1(caplog):
    # api data sometimes goes back in time
    caplog.set_level(logging.INFO)

    session = core.get_session(2020, 'testing', 3)
    session.load_laps()

    assert "The api attempted to rewrite history" in caplog.text  # the warning
    assert "Laps loaded and saved!" in caplog.text  # indicates success


@pytest.mark.f1telapi
def test_history_mod_2(caplog):
    # api data sometimes goes back in time
    caplog.set_level(logging.INFO)

    session = core.get_session(2020, 3, 'FP2')
    session.load_laps()

    assert "The api attempted to rewrite history" in caplog.text  # the error
    assert "Laps loaded and saved!" in caplog.text  # indicates success


@pytest.mark.f1telapi
def test_ergast_lookup_fail(caplog):
    # ergast lookup fails if data is requested to soon after a session ends
    caplog.set_level(logging.INFO)

    def fail_load():
        raise Exception
    core.ergast.load = fail_load  # force function call to fail

    session = core.get_session(2020, 3, 'FP2')  # rainy and short session, good for fast test/quick loading
    session.load_laps()

    assert "Ergast lookup failed" in caplog.text  # the warning
    assert "Laps loaded and saved!" in caplog.text  # indicates success
