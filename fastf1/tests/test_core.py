import pandas as pd

from fastf1 import core


def test_laps_constructor_metadata_propagation(reference_laps_data):
    session, laps = reference_laps_data

    assert laps.session is session
    assert laps.iloc[0:2].session is session
    assert laps.iloc[0].session is session


def test_laps_constructor_sliced():
    results = core.Laps({'A': [1, 2], 'B': [1, 2]})

    assert isinstance(results.iloc[0], pd.Series)
    assert isinstance(results.iloc[0], core.Lap)

    assert isinstance(results.loc[:, 'A'], pd.Series)
    assert not isinstance(results.loc[:, 'A'], core.Lap)


def test_session_results_constructor_sliced():
    results = core.SessionResults({'A': [1, 2], 'B': [1, 2]})

    assert isinstance(results.iloc[0], pd.Series)
    assert isinstance(results.iloc[0], core.DriverResult)

    assert isinstance(results.loc[:, 'A'], pd.Series)
    assert not isinstance(results.loc[:, 'A'], core.DriverResult)
