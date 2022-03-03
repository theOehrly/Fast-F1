import pytest

import fastf1.core
import fastf1.events


def test_get_session_deprecated():
    with pytest.warns(FutureWarning, match='deprecated'):
        session = fastf1.core.get_session(2021, 1, 'FP1')
    assert isinstance(session, fastf1.core.Session)
    assert session.event.year == 2021
    assert session.event.round_number == 1


def test_get_round_deprecated():
    with pytest.warns(FutureWarning, match='deprecated'):
        round_number = fastf1.core.get_round(2021, 'Bahrain')
    assert round_number == 1


def test_weekend_deprecated():
    with pytest.warns(FutureWarning, match='deprecated'):
        weekend = fastf1.core.Weekend(2021, 1)
    assert isinstance(weekend, fastf1.events.Event)
    assert weekend.year == 2021
    assert weekend.round_number == 1


def test_laps_constructor_metadata_propagation(reference_laps_data):
    session, laps = reference_laps_data

    assert laps.session is session
    assert laps.iloc[0:2].session is session
    assert laps.iloc[0].session is session
