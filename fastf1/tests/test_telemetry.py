import pytest

import pandas
import numpy

import fastf1.core
from fastf1.testing.reference_values import \
    (CAR_DATA_DTYPES, POS_DATA_DTYPES, ensure_data_type)


def test_constructor():
    tel = fastf1.core.Telemetry({'example': (1, 2, 3, 4, 5, 6)})
    sliced = tel.iloc[:2]
    assert isinstance(sliced, fastf1.core.Telemetry)


def test_base_class_view():
    tel = fastf1.core.Telemetry({'example': (1, 2, 3, 4, 5, 6)})
    bcv = tel.base_class_view
    assert isinstance(bcv, pandas.DataFrame)


def test_metadata_propagation_slicing():
    class Example:
        pass
    e = Example()

    tel = fastf1.core.Telemetry({'example': (1, 2, 3, 4, 5, 6)}, session=e)
    partial = tel.iloc[:2]
    assert hasattr(partial, 'session')
    assert isinstance(partial.session, Example)


def test_merging_with_metadata_propagation():
    class Example:
        pass
    e = Example()

    tel1 = fastf1.core.Telemetry({'example_1': (1, 2, 3, 4, 5, 6)}, session=e)
    tel2 = fastf1.core.Telemetry({'example_2': (1, 2, 3, 4, 5, 6)}, session=e)
    merged = tel1.merge(tel2, left_index=True, right_index=True)
    assert hasattr(merged, 'session')
    assert isinstance(merged.session, Example)
    assert merged.session is e
    assert all(col in merged.columns for col in ('example_1', 'example_2'))


def test_joining_with_metadata_propagation():
    class Example:
        pass

    e = Example()

    tel1 = fastf1.core.Telemetry({'example_1': (1, 2, 3, 4, 5, 6)}, session=e)
    tel2 = fastf1.core.Telemetry({'example_2': (1, 2, 3, 4, 5, 6)}, session=e)
    joined = tel1.join(tel2)
    assert hasattr(joined, 'session')
    assert isinstance(joined.session, Example)
    assert joined.session is e
    assert all(col in joined.columns for col in ('example_1', 'example_2'))


@pytest.mark.f1telapi
def test_merge_channels_with_metadata_propagation(reference_laps_data):
    session, laps = reference_laps_data
    lap = laps.pick_fastest()
    car_data = lap.get_car_data()
    pos_data = lap.get_pos_data()

    for freq in ('original', 10):
        merged = car_data.merge_channels(pos_data, frequency=freq)
        for attr in fastf1.core.Telemetry._metadata:
            assert getattr(merged, attr, None) is not None
        assert merged.session is session


@pytest.mark.f1telapi
def test_resample_channels_with_metadata_propagation(reference_laps_data):
    session, laps = reference_laps_data
    lap = laps.pick_fastest()
    car_data = lap.get_car_data()

    for freq in ('0.5S', '0.1S'):
        resampled = car_data.resample_channels(rule=freq)
        for attr in fastf1.core.Telemetry._metadata:
            assert getattr(resampled, attr, None) is not None
        assert resampled.session is session


@pytest.mark.f1telapi
def test_dtypes_from_api(reference_laps_data):
    session, laps = reference_laps_data
    for drv in session.car_data.keys():
        ensure_data_type(CAR_DATA_DTYPES, session.car_data[drv])

    for drv in session.pos_data.keys():
        ensure_data_type(POS_DATA_DTYPES, session.pos_data[drv])


@pytest.mark.f1telapi
def test_slice_by_time(reference_laps_data):
    session, laps = reference_laps_data
    drv = list(session.car_data.keys())[1]  # some driver
    test_data = session.car_data[drv]
    t0 = test_data['SessionTime'].iloc[1000]
    t1 = test_data['SessionTime'].iloc[2000]

    slice1 = test_data.slice_by_time(t0, t1)
    assert slice1['SessionTime'].iloc[0] == t0
    assert slice1['SessionTime'].iloc[-1] == t1
    assert len(slice1) == 1001
    ensure_data_type(CAR_DATA_DTYPES, slice1)

    dt = pandas.Timedelta(100, 'ms')
    slice2 = test_data.slice_by_time(t0-dt, t1+dt, interpolate_edges=True)
    assert slice2['SessionTime'].iloc[0] == t0 - dt
    assert slice2['SessionTime'].iloc[-1] == t1 + dt
    assert len(slice2) == 1003
    ensure_data_type(CAR_DATA_DTYPES, slice2)


@pytest.mark.f1telapi
def test_slice_by_mask(reference_laps_data):
    session, laps = reference_laps_data
    drv = list(session.car_data.keys())[1]  # some driver
    test_data = session.car_data[drv]
    mask = numpy.array([False, ] * len(test_data))
    mask[200:500] = True

    slice1 = test_data.slice_by_mask(mask)
    assert len(slice1) == 300
    assert slice1['SessionTime'].iloc[0] == test_data['SessionTime'].iloc[200]

    slice2 = test_data.slice_by_mask(mask, pad=2, pad_side='both')
    ref_mask = numpy.array([False, ] * len(test_data))
    ref_mask[198:502] = True
    assert len(slice2) == 304
    assert slice2['SessionTime'].iloc[0] == test_data['SessionTime'].iloc[198]


@pytest.mark.f1telapi
def test_slice_by_lap(reference_laps_data):
    session, laps = reference_laps_data
    drv = list(session.car_data.keys())[1]  # some driver
    test_data = session.car_data[drv]
    test_laps = laps.pick_driver(drv)

    lap2 = test_laps[test_laps['LapNumber'] == 2].iloc[0]
    lap3 = test_laps[test_laps['LapNumber'] == 3].iloc[0]
    lap2_3 = test_laps[(test_laps['LapNumber'] == 2) | (test_laps['LapNumber'] == 3)]

    tel2 = test_data.slice_by_lap(lap2)
    tel3 = test_data.slice_by_lap(lap3)
    tel2_3 = test_data.slice_by_lap(lap2_3)

    assert len(tel2) > 0
    assert len(tel3) > 0
    assert len(tel2_3) > 0
    assert len(tel2_3) == len(tel2) + len(tel3)


@pytest.mark.f1telapi
def test_merging_original_freq(reference_laps_data):
    session, laps = reference_laps_data
    lap = laps.pick_fastest()
    drv = lap['DriverNumber']
    test_car_data = session.car_data[drv].slice_by_lap(lap)
    test_pos_data = session.pos_data[drv].slice_by_lap(lap)
    merged = test_car_data.merge_channels(test_pos_data, frequency='original')

    ensure_data_type(CAR_DATA_DTYPES, merged)
    ensure_data_type(POS_DATA_DTYPES, merged)

    # test that all channels still exist
    channels = set(test_car_data.columns).union(set(test_pos_data.columns))
    for ch in channels:
        assert ch in merged.columns

    # test that merged number of samples is within 1% of sum of samples of the individual objects
    # some samples can overlap and therefore be combined during merging but should only happen for very few
    assert round((len(test_car_data) + len(test_pos_data)) / len(merged), 2) == 1.0

    # no values should be nan; everything should be interpolated
    assert not pandas.isnull(merged.to_numpy()).any()

    # check correct timing
    assert merged['Time'].iloc[0] == pandas.Timedelta(0)
    assert merged['SessionTime'].iloc[0] != pandas.Timedelta(0)


@pytest.mark.f1telapi
def test_merging_10_hz(reference_laps_data):
    session, laps = reference_laps_data
    lap = laps.pick_fastest()
    drv = lap['DriverNumber']
    test_car_data = session.car_data[drv].slice_by_lap(lap)
    test_pos_data = session.pos_data[drv].slice_by_lap(lap)
    merged = test_car_data.merge_channels(test_pos_data, frequency=10)

    ensure_data_type(CAR_DATA_DTYPES, merged)
    ensure_data_type(POS_DATA_DTYPES, merged)

    # test that all channels still exist
    channels = set(test_car_data.columns).union(set(test_pos_data.columns))
    for ch in channels:
        assert ch in merged.columns

    # assert correct number of samples for duration at 10 Hz within +-1 sample
    n_samples_target = round(test_car_data['Time'].iloc[-1].total_seconds() * 10, 0)
    assert len(merged) in (n_samples_target-1, n_samples_target, n_samples_target+1)

    # no values should be nan; everything should be interpolated
    assert not pandas.isnull(merged.to_numpy()).any()

    # check correct timing
    assert merged['Time'].iloc[0] == pandas.Timedelta(0)
    assert merged['SessionTime'].iloc[0] != pandas.Timedelta(0)


def test_drop_unknown_channels(caplog):
    fastf1.core.Telemetry.register_new_channel("test_keep", "discrete")
    data = {"Speed": [200, 202, 203],
            "test_keep": [1, 2, 3],
            "test_drop": [1, 2, 3]}

    tel = fastf1.core.Telemetry(data, drop_unknown_channels=False)
    assert "Speed" in tel.columns
    assert "test_keep" in tel.columns
    assert "test_drop" in tel.columns

    tel = fastf1.core.Telemetry(data, drop_unknown_channels=True)
    assert "Speed" in tel.columns
    assert "test_keep" in tel.columns
    assert "test_drop" not in tel.columns
    assert "unknown telemetry channels have been dropped" in caplog.text

    fastf1.core.Telemetry._CHANNELS.pop("test_keep")  # clean up


@pytest.mark.f1telapi
def test_resampling_down(reference_laps_data):
    session, laps = reference_laps_data
    lap = laps.pick_fastest()
    drv = lap['DriverNumber']
    test_data = session.car_data[drv].slice_by_lap(lap)

    test_data = test_data.resample_channels(rule='0.5S')

    # assert correct number of samples for duration at 2 Hz within +-1 sample
    n_samples_target = round(test_data['Time'].iloc[-1].total_seconds() * 2, 0)
    assert len(test_data) in (n_samples_target - 1, n_samples_target, n_samples_target + 1)

    # no values should be nan; everything should be interpolated
    assert not pandas.isnull(test_data.to_numpy()).any()

    # check correct timing
    assert test_data['Time'].iloc[0] == pandas.Timedelta(0)
    assert test_data['SessionTime'].iloc[0] != pandas.Timedelta(0)


@pytest.mark.f1telapi
def test_resampling_up(reference_laps_data):
    session, laps = reference_laps_data
    lap = laps.pick_fastest()
    drv = lap['DriverNumber']
    test_data = session.car_data[drv].slice_by_lap(lap)

    test_data = test_data.resample_channels(rule='0.05S')

    # assert correct number of samples for duration at 20 Hz within +-1 sample
    n_samples_target = round(test_data['Time'].iloc[-1].total_seconds() * 20, 0)
    assert len(test_data) in (n_samples_target - 1, n_samples_target, n_samples_target + 1)

    # no values should be nan; everything should be interpolated
    assert not pandas.isnull(test_data.to_numpy()).any()

    # check correct timing
    assert test_data['Time'].iloc[0] == pandas.Timedelta(0)
    assert test_data['SessionTime'].iloc[0] != pandas.Timedelta(0)


@pytest.mark.f1telapi
def test_add_driver_ahead(reference_laps_data):
    session, laps = reference_laps_data
    test_data = laps.pick_fastest().get_car_data()
    test_data = test_data.add_driver_ahead()
    # only first value may be NaN
    assert test_data['DistanceToDriverAhead'].isnull().sum() <= 1


@pytest.mark.f1telapi
def test_add_driver_ahead_resampled(reference_laps_data):
    session, laps = reference_laps_data
    test_data = laps.pick_fastest().get_car_data()\
        .resample_channels(rule='0.5S')
    test_data = test_data.add_driver_ahead()
    # only first value may be NaN
    assert test_data['DistanceToDriverAhead'].isnull().sum() <= 1


@pytest.mark.f1telapi
def test_add_track_status(reference_laps_data):
    session, laps = reference_laps_data

    test_data = laps.pick_driver('VER').get_telemetry()
    test_data = test_data.add_track_status()

    # Get statuses
    statuses = session.track_status['Status']

    # First and last track statuses must be equal to first and last
    # statuses
    assert test_data['TrackStatus'].iloc[0] == statuses.iloc[0]
    assert test_data['TrackStatus'].iloc[-1] == statuses.iloc[-1]


def create_sample_car_data():
    # create sample telemetry for testing the .add_* methods
    # which work with distance, only time and speed really needs
    # to make sense for that
    t0 = pandas.Timestamp(year=2020, month=5, day=7, hour=14)
    t1 = pandas.Timestamp(year=2020, month=5, day=7, hour=14, minute=1)
    dates = pandas.date_range(t0, t1, freq='261 ms')
    session_times = dates - t0
    times = session_times
    t = numpy.linspace(0, len(dates)*0.261, len(dates))
    speed = 80 + numpy.sqrt(320*t)

    tel = fastf1.core.Telemetry({
        'Time': times, 'SessionTime': session_times, 'Date': dates,
        'Source': 'car', 'Speed': speed, 'RPM': 9000, 'nGear': 7,
        'Throttle': 100, 'Brake': 0, 'DRS': 0
    })
    return tel


def test_add_distance():
    car_data = create_sample_car_data()
    car_data = car_data.add_distance()

    # check that the results make sense
    assert 'Distance' in car_data.columns
    assert car_data['Distance'].max() == car_data['Distance'].iloc[-1]
    # distance is analytically verified (+-10m due to numeric integration)
    assert car_data['Distance'].max().round(0) == 2867

    # set all distance values to zero and check that they stay zero
    car_data['Distance'] = 0
    car_data = car_data.add_distance(drop_existing=False)
    assert pandas.unique(car_data['Distance']) == [0, ]

    # now without drop_existing=False
    car_data = car_data.add_distance()
    assert car_data['Distance'].max().round(0) == 2867


def test_add_relative_distance():
    # test with no existing distance column first
    car_data = create_sample_car_data()
    car_data = car_data.add_relative_distance()

    # check that the results make sense
    assert 'RelativeDistance' in car_data.columns
    assert car_data['RelativeDistance'].max() == \
           car_data['RelativeDistance'].iloc[-1]
    assert car_data['RelativeDistance'].max() == 1.0
    assert car_data['RelativeDistance'].min() == 0.0

    # set all distance values to zero and check that they stay zero
    car_data['RelativeDistance'] = 0
    car_data = car_data.add_relative_distance(drop_existing=False)
    assert pandas.unique(car_data['RelativeDistance']) == [0, ]

    # now with drop existing = True
    car_data = car_data.add_relative_distance()
    assert car_data['RelativeDistance'].max().round(0) == 1.0

    # test with already existing distance column
    car_data = create_sample_car_data()
    car_data = car_data.add_distance().add_relative_distance()

    # check that the results make sense
    assert 'RelativeDistance' in car_data.columns
    assert car_data['RelativeDistance'].max() == \
           car_data['RelativeDistance'].iloc[-1]
    assert car_data['RelativeDistance'].max() == 1.0
    assert car_data['RelativeDistance'].min() == 0.0
