import pytest

import datetime

import pandas as pd
import pandas

import fastf1
from fastf1.testing.reference_values import LAP_DTYPES, ensure_data_type


def test_constructor():
    laps = fastf1.core.Laps({'example': (1, 2, 3, 4, 5, 6)})
    sliced = laps.iloc[:2]
    assert isinstance(sliced, fastf1.core.Laps)


def test_constructor_sliced():
    laps = fastf1.core.Laps({'example': (1, 2, 3, 4, 5, 6)})
    single = laps.iloc[:2].iloc[0]
    assert isinstance(single, fastf1.core.Lap)


def test_base_class_view_laps():
    laps = fastf1.core.Laps()
    bcv = laps.base_class_view
    assert isinstance(bcv, pandas.DataFrame)


@pytest.mark.f1telapi
def test_dtypes_from_api(reference_laps_data):
    session, laps = reference_laps_data
    ensure_data_type(LAP_DTYPES, laps)


def test_dtypes_default_columns():
    laps = fastf1.core.Laps(force_default_cols=True)
    ensure_data_type(LAP_DTYPES, laps)


@pytest.mark.f1telapi
def test_dtypes_pick(reference_laps_data):
    session, laps = reference_laps_data
    drv = list(laps['Driver'].unique())[1]  # some driver
    ensure_data_type(LAP_DTYPES, laps.pick_driver(drv))
    ensure_data_type(LAP_DTYPES, laps.pick_quicklaps())
    ensure_data_type(LAP_DTYPES, laps.iloc[:2])
    ensure_data_type(LAP_DTYPES,
                     laps.pick_driver(drv).iloc[:3].pick_quicklaps())


@pytest.mark.f1telapi
def test_laps_get_car_data(reference_laps_data):
    session, laps = reference_laps_data
    drv_laps = laps.pick_driver('BOT')
    car = drv_laps.get_car_data()
    assert car.shape == (26559, 10)
    assert not car.isna().sum().sum()  # sum rows then columns
    for col in ('Speed', 'RPM', 'nGear', 'Throttle', 'Brake', 'DRS',
                'Time', 'SessionTime', 'Date', 'Source'):
        assert col in car.columns


@pytest.mark.f1telapi
def test_laps_get_pos_data(reference_laps_data):
    session, laps = reference_laps_data
    drv_laps = laps.pick_driver('BOT')
    pos = drv_laps.get_pos_data()
    assert pos.shape == (29330, 8)
    assert not pos.isna().sum().sum()
    for col in ('X', 'Y', 'Z', 'Status', 'Time', 'SessionTime', 'Date',
                'Source'):
        assert col in pos.columns


@pytest.mark.f1telapi
def test_laps_get_telemetry(reference_laps_data):
    session, laps = reference_laps_data
    drv_laps = laps.pick_driver('BOT')
    tel = drv_laps.get_telemetry()
    assert tel.shape == (55788, 18)
    assert not tel.isna().sum().sum()
    for col in ('Speed', 'RPM', 'nGear', 'Throttle', 'Brake', 'DRS',
                'X', 'Y', 'Z', 'Status', 'Time', 'SessionTime', 'Date',
                'Source', 'Distance', 'DriverAhead'):
        assert col in tel.columns


@pytest.mark.f1telapi
def test_laps_get_weather_data(reference_laps_data):
    session, laps = reference_laps_data
    wd = laps.get_weather_data()
    assert wd.shape == (926, 8)
    for col in ('AirTemp', 'Humidity', 'Pressure', 'Rainfall',
                'TrackTemp', 'WindDirection', 'WindSpeed', 'Time'):
        assert col in wd.columns

    # test that an empty laps object returns empty weather data
    no_laps = fastf1.core.Laps()
    no_laps.session = session
    no_wd = no_laps.get_weather_data()
    assert isinstance(no_wd, pd.DataFrame)
    assert no_wd.empty
    for col in ('AirTemp', 'Humidity', 'Pressure', 'Rainfall',
                'TrackTemp', 'WindDirection', 'WindSpeed', 'Time'):
        assert col in wd.columns


@pytest.mark.f1telapi
def test_lap_get_car_data(reference_laps_data):
    session, laps = reference_laps_data
    drv_laps = laps.pick_fastest()
    car = drv_laps.get_car_data()
    assert car.shape == (340, 10)
    assert not car.isna().sum().sum()  # sum rows then columns
    for col in ('Speed', 'RPM', 'nGear', 'Throttle', 'Brake', 'DRS',
                'Time', 'SessionTime', 'Date', 'Source'):
        assert col in car.columns


@pytest.mark.f1telapi
def test_lap_get_pos_data(reference_laps_data):
    session, laps = reference_laps_data
    drv_laps = laps.pick_fastest()
    pos = drv_laps.get_pos_data()
    assert pos.shape == (377, 8)
    assert not pos.isna().sum().sum()
    for col in ('X', 'Y', 'Z', 'Status', 'Time', 'SessionTime', 'Date',
                'Source'):
        assert col in pos.columns


@pytest.mark.f1telapi
def test_lap_get_telemetry(reference_laps_data):
    session, laps = reference_laps_data
    drv_laps = laps.pick_fastest()
    tel = drv_laps.get_telemetry()
    assert tel.shape == (719, 18)
    # DistanceToDriverAhead may contain nan values
    assert not tel.loc[:, tel.columns != 'DistanceToDriverAhead']\
        .isna().sum().sum()
    for col in ('Speed', 'RPM', 'nGear', 'Throttle', 'Brake', 'DRS',
                'X', 'Y', 'Z', 'Status', 'Time', 'SessionTime', 'Date',
                'Source', 'Distance', 'DriverAhead'):
        assert col in tel.columns


@pytest.mark.f1telapi
def test_lap_get_weather_data(reference_laps_data):
    session, laps = reference_laps_data
    # check a valid lap
    fastest = laps.pick_fastest()
    wd = fastest.get_weather_data()
    assert wd.shape == (8, )
    for col in ('AirTemp', 'Humidity', 'Pressure', 'Rainfall',
                'TrackTemp', 'WindDirection', 'WindSpeed', 'Time'):
        assert col in wd.index

    # create a 'fake' lap for which no weather data exists
    # should use last known value
    lap = fastf1.core.Lap(index=fastest.index, dtype='object')
    lap.session = session
    lap['Time'] = datetime.timedelta(days=1/24*3)
    lap['LapStartTime'] = lap['Time'] - datetime.timedelta(seconds=30)
    wd_last = lap.get_weather_data()
    pd.testing.assert_series_equal(wd_last, session.weather_data.iloc[-1])


@pytest.mark.f1telapi
def test_laps_pick_laps(reference_laps_data):
    session, laps = reference_laps_data

    # one lap
    one_lap = laps.pick_laps(10)
    assert one_lap.shape == (19, 31)
    ensure_data_type(LAP_DTYPES, one_lap)

    # multiple laps
    mul_laps = laps.pick_laps([10, 20, 30])
    assert mul_laps.shape == (54, 31)
    ensure_data_type(LAP_DTYPES, mul_laps)

    # invalid input
    try:
        _ = laps.pick_laps(2.5)
    except ValueError as e:
        assert str(e) == "Invalid value 2.5 in `lap_numbers`"


@pytest.mark.f1telapi
def test_laps_pick_drivers(reference_laps_data):
    session, laps = reference_laps_data

    # one driver
    one_driver_abv = laps.pick_drivers("HAM")
    one_driver_number = laps.pick_drivers(44)
    assert one_driver_abv.shape == (53, 31)
    ensure_data_type(LAP_DTYPES, one_driver_abv)
    pd.testing.assert_frame_equal(one_driver_abv, one_driver_number)

    # multiple drivers
    mul_driver_mixed = laps.pick_drivers([5, "BOT", 7])
    assert mul_driver_mixed.shape == (112, 31)
    ensure_data_type(LAP_DTYPES, mul_driver_mixed)


@pytest.mark.f1telapi
def test_laps_pick_teams(reference_laps_data):
    session, laps = reference_laps_data

    # one team
    one_lap = laps.pick_teams("Mercedes")
    assert one_lap.shape == (106, 31)
    ensure_data_type(LAP_DTYPES, one_lap)

    # multiple teams
    mul_teams = laps.pick_teams(["Mercedes", "Ferrari"])
    # both Ferraris DNF
    assert mul_teams.shape == (136, 31)
    ensure_data_type(LAP_DTYPES, mul_teams)


@pytest.mark.f1telapi
def test_laps_pick_compounds(reference_laps_data):
    session, laps = reference_laps_data

    # one team
    one_compound = laps.pick_compounds("HARD")
    assert one_compound.shape == (172, 31)
    ensure_data_type(LAP_DTYPES, one_compound)

    # multiple compounds
    mul_compounds = laps.pick_compounds(["SOFT", "MEDIUM"])
    assert mul_compounds.shape == (754, 31)
    ensure_data_type(LAP_DTYPES, mul_compounds)


@pytest.mark.f1telapi
def test_laps_pick_track_status(reference_laps_data):
    session, laps = reference_laps_data

    # equals
    equals = laps.pick_track_status('2', how="equals")
    assert equals.shape == (48, 31)
    ensure_data_type(LAP_DTYPES, equals)

    # contains
    contains = laps.pick_track_status('4', how="contains")
    assert contains.shape == (115, 31)
    ensure_data_type(LAP_DTYPES, contains)

    # excludes
    excludes = laps.pick_track_status('4', how="excludes")
    assert excludes.shape == (811, 31)
    ensure_data_type(LAP_DTYPES, excludes)

    # any
    any_ = laps.pick_track_status('12', how="any")
    assert any_.shape == (848, 31)
    ensure_data_type(LAP_DTYPES, any_)

    # none
    none = laps.pick_track_status('46', how="none")
    assert none.shape == (811, 31)
    ensure_data_type(LAP_DTYPES, none)


@pytest.mark.f1telapi
@pytest.mark.parametrize("source", ["session_status", "timing_data"])
def test_split_quali_laps(source):
    session = fastf1.get_session(2023, 2, 'Q')
    session.load(telemetry=False, weather=False)

    if source == "session_status":
        # delete precalculated split times (from api parser)
        session._session_split_times = None

    q1, q2, q3 = session.laps.split_qualifying_sessions()

    assert len(q1['DriverNumber'].unique()) == 20
    assert len(q2['DriverNumber'].unique()) == 15
    assert len(q3['DriverNumber'].unique()) == 10


@pytest.mark.f1telapi
@pytest.mark.parametrize("source", ["session_status", "timing_data"])
def test_split_sprint_shootout_laps(source):
    session = fastf1.get_session(2023, 4, 'SS')
    session.load(telemetry=False, weather=False)

    if source == "session_status":
        # delete precalculated split times (from api parser)
        session._session_split_times = None

    q1, q2, q3 = session.laps.split_qualifying_sessions()

    assert len(q1['DriverNumber'].unique()) == 20

    # Logan Sargeant was 15th in Q1 but crashed and couldn't participate in Q2
    assert len(q2['DriverNumber'].unique()) == 14
    assert len(q3['DriverNumber'].unique()) == 9


@pytest.mark.f1telapi
@pytest.mark.parametrize("source", ["session_status", "timing_data"])
def test_calculated_quali_results(source):
    session = fastf1.get_session(2023, 4, 'Q')
    session.load(telemetry=False, weather=False)

    # copy and delete (!) before recalculating
    ergast_results = session.results.copy()
    session.results.loc[:, ('Q1', 'Q2', 'Q3')] = pd.NaT

    if source == "session_status":
        # delete precalculated split times (from api parser)
        session._session_split_times = None

    session._calculate_quali_like_session_results(force=True)

    # Note that differences may exist if one or more drivers didn't set a
    # proper lap time in any of the Quali sessions. In this case, Ergast may
    # still return a (very slow) lap time, while the calculation will return
    # NaT. This is acceptable. Testing is done on a session where this is not
    # an issue.
    pd.testing.assert_frame_equal(ergast_results, session.results)


@pytest.mark.f1telapi
@pytest.mark.parametrize("source", ["session_status", "timing_data"])
def test_quali_q3_cancelled(source):
    session = fastf1.get_session(2023, 4, 'Q')
    session.load(telemetry=False, weather=False)

    # Remove Q3 to simulate cancelled Q3. If a future race has a cancelled Q3,
    # that would be a better test case. The last one was the US GP in 2015, so
    # no lap data is available.
    session.session_status.drop([13, 14, 15, 16], inplace=True)
    session.results['Q3'] = pd.NaT
    if source == "session_status":
        # delete precalculated split times (from api parser)
        session._session_split_times = None
    else:
        session._session_split_times.pop(-1)

    # Test split_qualifying_sessions()
    q1, q2, q3 = session.laps.split_qualifying_sessions()

    assert len(q1['DriverNumber'].unique()) == 20
    assert len(q2['DriverNumber'].unique()) == 15
    assert q3 is None

    # Test _calculate_quali_like_session_results()
    # copy and delete (!) before recalculating
    orig_results = session.results.copy()
    session.results.loc[:, ('Q1', 'Q2', 'Q3')] = pd.NaT
    session._calculate_quali_like_session_results(force=True)

    # Note that differences may exist if one or more drivers didn't set a
    # proper lap time in any of the Quali sessions. In this case, Ergast may
    # still return a (very slow) lap time, while the calculation will return
    # NaT. This is acceptable. Testing is done on a session where this is not
    # an issue.
    pd.testing.assert_series_equal(
        session.results['Q1'].sort_values(), orig_results['Q1'].sort_values())
    pd.testing.assert_series_equal(
        session.results['Q2'].sort_values(), orig_results['Q2'].sort_values())
    assert session.results['Q3'].isna().all()
