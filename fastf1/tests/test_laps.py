import pytest
import fastf1
import pandas
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
    drv = list(laps['Driver'].unique())[1]  # some driver
    drv_laps = laps.pick_driver(drv)
    car = drv_laps.get_car_data()
    assert car.shape == (26559, 10)
    assert not car.isna().sum().sum()  # sum rows then columns
    for col in ('Speed', 'RPM', 'nGear', 'Throttle', 'Brake', 'DRS',
                'Time', 'SessionTime', 'Date', 'Source'):
        assert col in car.columns


@pytest.mark.f1telapi
def test_laps_get_pos_data(reference_laps_data):
    session, laps = reference_laps_data
    drv = list(laps['Driver'].unique())[1]  # some driver
    drv_laps = laps.pick_driver(drv)
    pos = drv_laps.get_pos_data()
    assert pos.shape == (29330, 8)
    assert not pos.isna().sum().sum()
    for col in ('X', 'Y', 'Z', 'Status', 'Time', 'SessionTime', 'Date',
                'Source'):
        assert col in pos.columns


@pytest.mark.f1telapi
def test_laps_get_telemetry(reference_laps_data):
    session, laps = reference_laps_data
    drv = list(laps['Driver'].unique())[1]  # some driver
    drv_laps = laps.pick_driver(drv)
    tel = drv_laps.get_telemetry()
    assert tel.shape == (55788, 18)
    assert not tel.isna().sum().sum()
    for col in ('Speed', 'RPM', 'nGear', 'Throttle', 'Brake', 'DRS',
                'X', 'Y', 'Z', 'Status', 'Time', 'SessionTime', 'Date',
                'Source', 'Distance', 'DriverAhead'):
        assert col in tel.columns


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
