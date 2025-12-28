import warnings
from fastf1.utils.warnings import FastF1DataWarning
from fastf1.internals.pandas_extensions import _fallback_create_df
import pytest

def test_warning_on_fallback_dataframe_creation():
    arrays = [[1, 2, 3], [4, 5, 6]]
    columns = ['A', 'B']

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _fallback_create_df(arrays, columns)

        assert any(issubclass(warn.category, FastF1DataWarning) for warn in w)