# test some known special cases

import logging

import pandas as pd
import pytest

import fastf1
import fastf1.ergast
import fastf1.testing
from fastf1 import _api
from fastf1.testing.reference_values import LAP_DTYPES


@pytest.mark.f1telapi
def test_ergast_lookup_fail():
    cache_dir = fastf1.Cache._CACHE_DIR
    fastf1.testing.run_in_subprocess(_test_ergast_lookup_fail, cache_dir)


def _test_ergast_lookup_fail(cache_dir):
    from fastf1.logger import LoggingManager
    LoggingManager.debug = False
    # special, relevant on Linux only.
    # debug=True does not propagate to subprocess on windows

    fastf1.Cache.enable_cache(cache_dir)
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
    assert session.laps.pick_drivers('SAI').shape[0] == 14


@pytest.mark.f1telapi
def test_crash_lap_added_2():
    # verstappen crashed on his first lap, the lap needs to exist
    session = fastf1.get_session(2021, 'British Grand Prix', 'R')

    session.load(telemetry=False)
    assert session.laps.pick_drivers('VER').shape[0] == 1


@pytest.mark.f1telapi
def test_no_extra_lap_if_race_not_started():
    # tsunoda had a technical issue shortly before the race and could not
    # start even though he is listed in the drivers list
    session = fastf1.get_session(2022, 2, 'R')

    session.load(telemetry=False, weather=False)
    assert session.laps.size
    assert session.laps.pick_drivers('TSU').size == 0


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

    fastf1._api.timing_app_data = _mock

    session = fastf1.get_session(2020, 'Italy', 'R')
    session.load(telemetry=False, weather=False)

    assert 'Failed to load lap data!' not in log_handle.text
    assert 'No tyre data for driver' in log_handle.text

    assert session.laps.size
    assert all([col in session.laps.columns for col in LAP_DTYPES.keys()])


@pytest.mark.f1telapi
def test_inlap_added():
    session = fastf1.get_session(2021, 'Mexico City', 'Q')
    session.load(telemetry=False)

    last = session.laps.pick_drivers('PER').iloc[-1]
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
    ver_laps = session.laps.pick_drivers('VER')
    idx = ver_laps[(ver_laps['Time'] > restart_time)
                   & pd.notna(ver_laps['Time'])].index[0]
    assert ver_laps.loc[idx]['LapStartTime'] > restart_time


@pytest.mark.f1telapi
def test_partial_lap_retired_added():
    # test that a last (partial) lap is added for drivers that retire on track
    session = fastf1.get_session(2022, 1, 'R')
    session.load()

    assert session.laps.pick_drivers('11').iloc[-1]['FastF1Generated']


@pytest.mark.f1telapi
def test_partial_lap_retired_not_added_after_finished():
    # in some cases, the code that generates a partial last lap when a driver
    # retires on track would add a nonexistent last lap after the race has
    # fished for the first (few) driver(s) that cross the finish line
    # this is because the session status timestamps are slightly off and
    # generally delayed by a few hundred milliseconds
    # ensure that no lap is added if a driver has completed the race distance
    session = fastf1.get_session(2021, 21, 'R')
    session.load()

    assert (session.laps.pick_drivers('HAM')['LapNumber'].max()
            == session.total_laps)


@pytest.mark.f1telapi
def test_first_lap_time_added_from_ergast_in_race():
    session = fastf1.get_session(2022, 1, 'R')
    session.load(telemetry=False)

    assert not pd.isna(session.laps.pick_laps(1)['LapTime']).any()

@pytest.mark.f1telapi
def test_lap_start_time_dtype_single_lap():
    # When a driver only completes one lap, the LapStartTime column only
    # contains a NaT value. Ensure that this column still has the correct
    # timedelta64 dtype as pandas defaults to datetime64[ns] when all values
    # are NaT (see GH#674)
    session = fastf1.get_session(2022, 10, 1)
    session.load(telemetry=False, weather=False)

    assert session.laps['LapStartTime'].dtype == 'timedelta64[ns]'

@pytest.mark.f1telapi
def test_consecutive_equal_lap_times():
    # No update for the lap time value is given if the lap time is exactly
    # equal to the previous value. Ensure that this is recognized and corrected
    # by calculating the lap time from the sector times.
    session = fastf1.get_session(2023, 1, 'R')
    session.load(telemetry=False, weather=False)
    lt = session.laps.pick_drivers('16')

    assert lt.pick_laps(37)['LapTime'].iloc[0] == pd.Timedelta(seconds=97.170)

    assert lt.pick_laps(37)['LapTime'].iloc[0] \
           == lt.pick_laps(38)['LapTime'].iloc[0]


@pytest.mark.f1telapi
def test_consecutive_equal_sector_times():
    # No update for a sector time value is given if the sector time is exactly
    # equal to the previous value. Ensure that this is recognized and corrected
    # by calculating the sector time from the lap time and the other sector
    # times.
    session = fastf1.get_session(2023, 1, 'R')
    session.load(telemetry=False, weather=False)
    lt = session.laps.pick_drivers('21')

    assert lt.pick_laps(20)['Sector1Time'].iloc[0] \
           == pd.Timedelta(seconds=31.442)
    assert lt.pick_laps(19)['Sector1Time'].iloc[0] \
           == lt.pick_laps(20)['Sector1Time'].iloc[0]


@pytest.mark.f1telapi
def test_laps_aligned_across_drivers():
    # Without postprocessing, lap start and end times are not correctly aligned
    # between drivers. Test that this is done correctly by calculating the
    # gap to the leader for all drivers at the end of the race and compare
    # with the official classification
    session = fastf1.get_session(2023, 1, 'R')
    session.load(telemetry=False, weather=False)

    ref = {
        '11': pd.Timedelta(seconds=11.987),
        '14': pd.Timedelta(seconds=38.637),
        '55': pd.Timedelta(seconds=48.052),
        '44': pd.Timedelta(seconds=50.977),
        '18': pd.Timedelta(seconds=54.502),
        '63': pd.Timedelta(seconds=55.873),
        '77': pd.Timedelta(seconds=72.647),
        '10': pd.Timedelta(seconds=73.753),
        '23': pd.Timedelta(seconds=89.774),
        '22': pd.Timedelta(seconds=90.870),
    }

    leader = session.results['DriverNumber'].iloc[0]
    leader_time = session.laps.pick_drivers(leader).iloc[-1]['Time']
    finished = (session.results['Status'] == 'Finished')
    for drv in session.results.loc[finished, 'DriverNumber'].iloc[1:]:
        other_time = session.laps.pick_drivers(drv).iloc[-1]['Time']
        assert (other_time - leader_time) == ref[drv]


@pytest.mark.f1telapi
@pytest.mark.parametrize(
    'year, round_',
    (
        (2020, 15),
        (2023, 1),
        (2024, 4),
    )
)
def test_laps_aligned_consistency(year, round_):
    # Test that the lap time alignment algorithm works correctly, by running
    # it twice. If the laps were aligned correctly the first time, nothing
    # should change the second time.
    session = fastf1.get_session(year, round_, 'R')

    # get laps_data from parser, this is already aligned once
    laps_data, stream_data, _ = _api._extended_timing_data(session.api_path)

    laps_data_ref = laps_data.copy()

    # align again, if everything is correct, nothing must change here
    _api._align_laps(laps_data, stream_data)

    pd.testing.assert_frame_equal(laps_data, laps_data_ref)


@pytest.mark.f1telapi
def test_explicitly_missing_lap_times_calculated():
    # Russel had transponder issues in bahrain 2025, which caused the timing
    # problems. Two lap times were missing but the source explicitly indicated
    # {'value': ''} instead of simply skipping over the data.
    # Check that in cases of explicitly missing lap times, where we know for
    # sure that data wasn't just parsed incorrectly, the lap times are
    # calculated from the sector times.
    session = fastf1.get_session(2025, 4, 'R')
    session.load(telemetry=False, weather=False)
    l37 = session.laps.pick_drivers('63').pick_laps(37)

    assert not l37['LapTime'].isna().any()


@pytest.mark.f1telapi
@pytest.mark.parametrize(
    "year, round_, session, drv, stints",
    (
        # 2025 Australian GP Race, only two drivers had issues (GH#715)
        (2025, "Australia", "Race", "BOR",
         [([1, 33], "INTERMEDIATE"),
          ([34, 44], "MEDIUM"),
          ([45, 46], "INTERMEDIATE")]),

        (2025, "Australia", "Race", "BEA",
         [([1, 39], "INTERMEDIATE"),
          ([40, 44], "MEDIUM"),
          ([45, 57], "INTERMEDIATE")]),

        # 2025 Miami GP Sprint, all drivers have incorrect tyre data (GH#742)
        (2025, "Miami", "Sprint", "VER",
         [([1, 12], "INTERMEDIATE"),
          ([13, 18], "SOFT")]),

        (2025, "Miami", "Sprint", "RUS",
         [([1, 13], "INTERMEDIATE"),
          ([14, 18], "MEDIUM")]),

        # special case: ANT went into the pits on lap 13 but couldn't change
        # tyres because his box was blocked so he exited without changing and
        # only changed in lap 14. There's some chaos in the data around this.
        (2025, "Miami", "Sprint", "ANT",
         [([1, 13], "INTERMEDIATE"),
          ([14, 18], "MEDIUM")]),
    )
)
def test_tyre_data_incorrect_stint_counter(year, round_, session, drv, stints):
    session = fastf1.get_session(year, round_, session)
    session.load(telemetry=False, weather=False)

    for (start, end), compound in stints:
        assert (
                session.laps.pick_drivers(drv)
                .pick_laps(range(start, end + 1))['Compound']
                == compound
        ).all()
