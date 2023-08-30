import pytest

import pandas as pd

import fastf1
from fastf1.core import DriverResult, Lap, Laps, SessionResults
from fastf1.ergast import Ergast


@pytest.mark.f1telapi
def test_lap_data_loading_position_calculation():
    # compare internally calculated per-lap positions with data from ergast
    session = fastf1.get_session(2023, 1, 'R')
    session.load(telemetry=False, weather=False)

    ergast = Ergast()
    ergast_laps = ergast.get_lap_times(
        season=2023, round=1, limit=20 * 60
    ).content[0]
    ergast_drivers = ergast.get_driver_info(season=2023)

    for i, drv_id in enumerate(ergast_laps['driverId'].unique()):
        # get driver abbreviation from ergast driverId
        abb = ergast_drivers[
            ergast_drivers['driverId'] == drv_id
        ]['driverCode'].iloc[0]

        erg_drv_laps = ergast_laps[ergast_laps['driverId'] == drv_id]
        drv_laps = session.laps.pick_drivers(abb)

        # subtract per-lap positions between the data sources
        delta = erg_drv_laps['position'].reset_index(drop=True) \
            - drv_laps['Position'].reset_index(drop=True)

        # number of laps may differ (FastF1 adds a last crash lap for example)
        # therefore, fill NaN with 0.0 for no delta
        delta = delta.fillna(value=0.0)

        assert (delta == 0).all()  # assert that the delta is zero for all laps


def test_laps_constructor_metadata_propagation(reference_laps_data):
    session, laps = reference_laps_data

    assert laps.session is session
    assert laps.iloc[0:2].session is session
    assert laps.iloc[0].session is session


def test_laps_constructor_sliced():
    results = Laps({'A': [1, 2], 'B': [1, 2]})

    assert isinstance(results.iloc[0], pd.Series)
    assert isinstance(results.iloc[0], Lap)

    assert isinstance(results.loc[:, 'A'], pd.Series)
    assert not isinstance(results.loc[:, 'A'], Lap)


def test_session_results_constructor_sliced():
    results = SessionResults({'A': [1, 2], 'B': [1, 2]})

    assert isinstance(results.iloc[0], pd.Series)
    assert isinstance(results.iloc[0], DriverResult)

    assert isinstance(results.loc[:, 'A'], pd.Series)
    assert not isinstance(results.loc[:, 'A'], DriverResult)
