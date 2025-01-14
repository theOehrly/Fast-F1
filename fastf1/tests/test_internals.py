from typing import Optional

import numpy as np
import pandas as pd
import pytest

from fastf1.internals.pandas_base import (
    BaseDataFrame,
    BaseSeries,
    _BaseSeriesConstructor
)
from fastf1.internals.pandas_extensions import _unsafe_create_df_fast


def test_pandas_base_internal_imports():
    # ensure that the internal import (still) works and ensure that the
    # fallback resolves to the same type
    from pandas.core.internals import SingleBlockManager

    FallbackSingleBlockManager = type(getattr(pd.Series(dtype=float), '_mgr'))
    assert SingleBlockManager is FallbackSingleBlockManager


def test_fast_df_creation():
    data = {'A': [1, 2, 3], 'B': [1.0, 2.0, 3.0], 3: ['a', 'b', 'c']}

    # need to explicitly force numpy dtypes to match pandas defaults
    dtypes = ['int64', 'float64', 'object']

    df_safe = pd.DataFrame(data)

    arrays = list(np.array(d, dtype=t) for d, t in zip(data.values(), dtypes))
    df_fast = _unsafe_create_df_fast(
        arrays=arrays, columns=list(data.keys())
    )

    pd.testing.assert_frame_equal(df_safe, df_fast)


def test_base_frame_slicing_default():
    class TestDataFrame(BaseDataFrame):
        pass

    df = TestDataFrame({'A': [10, 11, 12], 'B': [20, 21, 22]})
    assert isinstance(df, TestDataFrame)
    assert isinstance(df, pd.DataFrame)

    df_sliced = df.iloc[0:2]
    assert isinstance(df_sliced, TestDataFrame)
    assert isinstance(df_sliced, pd.DataFrame)
    assert (df_sliced
            == pd.DataFrame({'A': [10, 11], 'B': [20, 21]})
            ).all().all()

    vert_ser = df.loc[:, 'A']
    assert isinstance(vert_ser, pd.Series)
    assert (vert_ser == pd.Series([10, 11, 12])).all()

    hor_ser = df.iloc[0]
    assert isinstance(hor_ser, pd.Series)
    assert (hor_ser == pd.Series({'A': 10, 'B': 20})).all()


def test_base_frame_slicing():
    class TestSeriesVertical(pd.Series):
        pass

    class TestSeriesHorizontal(BaseSeries):
        pass

    class TestDataFrame(BaseDataFrame):
        @property
        def _constructor_sliced_vertical(self):
            return TestSeriesVertical

        @property
        def _constructor_sliced_horizontal(self):
            return TestSeriesHorizontal

    df = TestDataFrame({'A': [10, 11, 12], 'B': [20, 21, 22]})
    assert isinstance(df, TestDataFrame)
    assert isinstance(df, pd.DataFrame)

    df_sliced = df.iloc[0:2]
    assert isinstance(df_sliced, TestDataFrame)
    assert isinstance(df_sliced, pd.DataFrame)
    assert (df_sliced
            == pd.DataFrame({'A': [10, 11], 'B': [20, 21]})
            ).all().all()

    vert_ser = df.loc[:, 'A']
    assert isinstance(vert_ser, TestSeriesVertical)
    assert isinstance(vert_ser, pd.Series)
    assert (vert_ser == pd.Series([10, 11, 12])).all()

    hor_ser = df.iloc[0]
    assert isinstance(hor_ser, TestSeriesHorizontal)
    assert isinstance(hor_ser, pd.Series)
    assert (hor_ser == pd.Series({'A': 10, 'B': 20})).all()

    # iterrows initializes row series from ndarray not blockmanager
    for _, row in df.iterrows():
        assert isinstance(row, TestSeriesHorizontal)
        assert isinstance(row, pd.Series)


def test_base_series_slicing():
    class TestSeries(BaseSeries):
        pass

    series = TestSeries([0, 1, 2, 3])
    ser_sliced = series.iloc[0:2]
    assert (ser_sliced == pd.Series([0, 1])).all()
    assert isinstance(ser_sliced, BaseSeries)
    assert isinstance(ser_sliced, pd.Series)


def test_base_frame_metadata_propagation():
    class TestSeriesHorizontal(BaseSeries):
        _metadata = ['some_value']

    class TestSeriesVertical(BaseSeries):
        pass

    class TestDataFrame(BaseDataFrame):
        _metadata = ['some_value']

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.some_value = None

        @property
        def _constructor_sliced_horizontal(self):
            return TestSeriesHorizontal

        @property
        def _constructor_sliced_vertical(self):
            return TestSeriesVertical

    df = TestDataFrame({'A': [10, 11, 12], 'B': [20, 21, 22]})
    df.some_value = 100

    # propagation to dataframe slice
    df_sliced = df.iloc[0:2]
    assert df_sliced.some_value == 100

    # no propagation to a series object that does not define this metadata
    vert_slice = df.loc[:, 'A']
    assert not hasattr(vert_slice, 'some_value')

    # propagation to a series object that does define the same metadata
    hor_slice = df.iloc[0]
    assert hor_slice.some_value == 100

    # iterrows initializes row series from ndarray not blockmanager
    for _, row in df.iterrows():
        assert row.some_value == 100


def test_base_series_metadata_propagation():
    class TestSeries(BaseSeries):
        _metadata = ['some_value']

    series = TestSeries([0, 1, 2, 3])
    series.some_value = 100
    ser_sliced = series.iloc[0:2]
    assert ser_sliced.some_value == 100


@pytest.mark.parametrize(
    "test_data", ([0, 1, 2, 3], pd.Series([0, 1, 2, 3]))
)
def test_base_series_constructor_direct_fallback(test_data):
    # If for whatever reason the _BaseSeriesConstructor is not called as
    # intended as _constructor_sliced from a BaseDataFrame but instead
    # unplanned from anywhere else, it should fall back to behaving as if
    # a pandas.Series object is created directly.
    series_a = _BaseSeriesConstructor(test_data)
    series_b = pd.Series(test_data)

    assert not isinstance(series_a, _BaseSeriesConstructor)
    assert isinstance(series_a, pd.Series)
    assert (series_a == series_b).all()


def test_base_frame_default_columns():

    class TestDataFrame(BaseDataFrame):

        _COLUMNS = {
            'A': int,
            'B': 'float64',
            'C': object,
            'D': 'object',
            'E': Optional[int],
            'F': 'string[python]',
            'G': str,
            'known': 'string[python]'
        }


    df = TestDataFrame({'unknown': [1, 2, 3], 'known': ['a', 'b', 'c']},
                       _force_default_cols=True)

    for key in TestDataFrame._COLUMNS.keys():
        assert key in df.columns

    assert 'unknown' not in df.columns

    assert df['A'].dtype == np.int64
    assert df['B'].dtype == np.float64
    assert df['C'].dtype == np.dtype('O')
    assert df['D'].dtype == np.dtype('O')
    assert df['E'].dtype == np.dtype('O')
    assert df['F'].dtype == 'string[python]'

    assert df['A'].iloc[0] == 0
    assert np.isnan(df['B'].iloc[0])
    assert df['C'].iloc[0] is None
    assert df['D'].iloc[0] is None
    assert df['E'].iloc[0] is None
    assert pd.isna(df['F'].iloc[0])
    assert df['G'].iloc[0] == ""
    assert df['known'].iloc[0] == "a"
