import pandas as pd
import pytest

import fastf1
from fastf1.core import (
    DriverResult,
    Lap,
    Laps,
    Session,
    SessionResults
)
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


@pytest.mark.f1telapi
def test_first_lap_pitout_times():
    sprint_session = fastf1.get_session(2023, 4, "Sprint")
    sprint_session.load(telemetry=False, weather=False, messages=False)
    sprint_laps = sprint_session.laps
    sprint_mask = (sprint_laps["LapNumber"] == 1) & \
                  (~sprint_laps["PitOutTime"].isna())
    assert sprint_laps[sprint_mask]["Driver"].tolist() == ["OCO"]

    race_session = fastf1.get_session(2023, 5, "R")
    race_session.load(telemetry=False, weather=False, messages=False)
    race_laps = race_session.laps
    race_mask = (race_laps["LapNumber"] == 1) & \
                (~race_laps["PitOutTime"].isna())
    assert race_laps[race_mask]["Driver"].tolist() == []


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


def test_add_lap_status_to_laps():
    # TODO: It should really be possible to mock a session object instead of
    #   modifying an existing one like here. This is incredibly hack.
    session = fastf1.get_session(2020, 'Italy', 'R')

    laps = Laps(
        [[pd.Timedelta(minutes=1), pd.Timedelta(minutes=2)],
         [pd.Timedelta(minutes=2), pd.Timedelta(minutes=3)],
         [pd.Timedelta(minutes=3), pd.Timedelta(minutes=4)],
         [pd.Timedelta(minutes=4), pd.Timedelta(minutes=5)],
         [pd.Timedelta(minutes=5), pd.Timedelta(minutes=6)],
         [pd.Timedelta(minutes=6), pd.Timedelta(minutes=7)],
         [pd.Timedelta(minutes=7), pd.Timedelta(minutes=8)]],
        _force_default_cols=False,
        columns=('LapStartTime', 'Time')
    )

    status = pd.DataFrame(
        [[pd.Timedelta(minutes=0), '1', 'AllClear'],
         [pd.Timedelta(minutes=2.5), '2', 'Yellow'],
         [pd.Timedelta(minutes=3.25), '6', 'VSCDeployed'],
         [pd.Timedelta(minutes=3.75), '7', 'VSCEnding'],
         [pd.Timedelta(minutes=4.25), '1', 'AllClear'],
         [pd.Timedelta(minutes=6.5), '2', 'Yellow']],
        columns=('Time', 'Status', 'Message')
    )

    # modify and reuse the existing session (very hacky but ok here)
    session._track_status = status
    session._add_track_status_to_laps(laps)

    expected_per_lap_status = ['1', '12', '267', '71', '1', '12', '2']

    assert (laps['TrackStatus'] == expected_per_lap_status).all()


def test_rcm_parsing_deleted_laps():
    session = fastf1.get_session(2024, 5, 'SQ')
    session.load(telemetry=False, weather=False)

    assert session.laps['Deleted'].sum() == 6

    # Norris' lap was deleted and then reinstated
    # ensure that this is correctly handled
    q1, q2, q3 = session.laps.split_qualifying_sessions()
    fastest = q3.pick_fastest()
    assert fastest['Driver'] == 'NOR'
    assert (fastest['LapTime']
            == pd.Timedelta(minutes=1, seconds=57, milliseconds=940))
    assert not fastest['Deleted']
    assert fastest['DeletedReason'] == ""
    assert fastest['IsPersonalBest']


def test_tyre_data_parsing():
    session = fastf1.get_session(2024, 'Silverstone', 'FP1')
    session.load(telemetry=False)

    ver = session.laps.pick_drivers('VER')

    ref = pd.DataFrame(
        [[1.0, 'HARD', True, 1.0], [1.0, 'HARD', True, 2.0],
         [1.0, 'HARD', True, 3.0], [1.0, 'HARD', True, 4.0],
         [1.0, 'HARD', True, 5.0], [2.0, 'HARD', False, 6.0],
         [2.0, 'HARD', False, 7.0], [2.0, 'HARD', False, 8.0],
         [3.0, 'MEDIUM', True, 1.0], [3.0, 'MEDIUM', True, 2.0],
         [3.0, 'MEDIUM', True, 3.0], [3.0, 'MEDIUM', True, 4.0],
         [3.0, 'MEDIUM', True, 5.0], [4.0, 'HARD', False, 9.0],
         [4.0, 'HARD', False, 10.0], [4.0, 'HARD', False, 11.0],
         [4.0, 'HARD', False, 12.0], [4.0, 'HARD', False, 13.0],
         [4.0, 'HARD', False, 14.0], [4.0, 'HARD', False, 15.0],
         [4.0, 'HARD', False, 16.0], [4.0, 'HARD', False, 17.0],
         [4.0, 'HARD', False, 18.0], [4.0, 'HARD', False, 19.0],
         [4.0, 'HARD', False, 20.0]],
        columns=['Stint', 'Compound', 'FreshTyre', 'TyreLife']
    )

    compare = ver[['Stint', 'Compound', 'FreshTyre', 'TyreLife']]
    assert compare.equals(ref)


def test_session_results_drivers():
    # Sainz (55) is replaced by Bearman (38) after FP2
    session = fastf1.get_session(2024, "Saudi Arabia", 2)
    session.load(laps=False, telemetry=False, weather=False)
    drivers = session.results.index
    assert "55" in drivers
    assert "38" not in drivers

    session = fastf1.get_session(2024, "Saudi Arabia", 3)
    session.load(laps=False, telemetry=False, weather=False)
    drivers = session.results.index
    assert "38" in drivers
    assert "55" not in drivers

    # Mick Schumacher (47) is not officially classified
    # and does not appear in the F1 API response
    session = fastf1.get_session(2022, "Saudi Arabia", "R")
    session.load(laps=False, telemetry=False, weather=False)
    drivers = session.results.index
    assert "47" in drivers
