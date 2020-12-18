import fastf1
import pandas
from tests.reference_values import LAP_DTYPES, ensure_data_type


fastf1.Cache.enable_cache("test_cache/")
EXP_SESSION = fastf1.get_session(2020, 'Italy', 'R')
EXP_LAPS = EXP_SESSION.load_laps()


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


def test_dtypes_from_api():
    ensure_data_type(LAP_DTYPES, EXP_LAPS)


def test_dtypes_pick():
    drv = list(EXP_LAPS['Driver'].unique())[1]  # some driver
    ensure_data_type(LAP_DTYPES, EXP_LAPS.pick_driver(drv))
    ensure_data_type(LAP_DTYPES, EXP_LAPS.pick_quicklaps())
    ensure_data_type(LAP_DTYPES, EXP_LAPS.iloc[:2])
    ensure_data_type(LAP_DTYPES, EXP_LAPS.pick_driver(drv).iloc[:3].pick_quicklaps())
