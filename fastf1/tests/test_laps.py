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
