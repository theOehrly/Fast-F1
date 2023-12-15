from fastf1.internals.pandas_base import BaseDataFrame, BaseSeries
from fastf1.internals.pandas_extensions import _unsafe_create_df_fast

import numpy as np
import pandas as pd


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
