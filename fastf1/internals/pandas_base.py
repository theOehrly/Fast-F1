"""Base classes for objects that inherit form Pandas Series or DataFrame."""
from typing import (
    Callable,
    Optional,
    final
)

import pandas as pd


# dangerous import of pandas internals
# these imports are covered by
# test_internals.py::test_pandas_base_internal_imports
# to detect any failures as soon as possible
try:
    from pandas.core.internals import SingleBlockManager
except ImportError as exc:
    _mgr_instance = getattr(pd.Series(dtype=float), '_mgr')
    if _mgr_instance is None:
        raise ImportError("Import of Pandas internals failed. You are likely "
                          "using a recently released version of Pandas that "
                          "isn't yet supported. Please report this issue. In"
                          "the meantime, you can try downgrading to an older "
                          "version of Pandas.") from exc
    SingleBlockManager = type(_mgr_instance)


class BaseDataFrame(pd.DataFrame):
    """Base class for objects that inherit from ``pandas.DataFrame``.

    A DataFrame-like slice of an object that inherits from this class will
    be of equivalent type as the object that it is created from (instead of
    being a Pandas DataFrame).

    A Series-like slice of an object that inherits from this class will by
    default be a normal Pandas Series. An extension to pandas'
    `._constructor_sliced` is implemented in this class to allow using
    different return types for the created Series-like slices of an object
    depending on whether the DataFrame is sliced vertically or horizontally.
    For this, the additional properties ``_constructor_sliced_horizontal``
    and ``_constructor_sliced_vertical`` are introduced. Both properties are
    set to ``pandas.Series`` by default and only need to be overwritten when
    a different type is desired.
    """
    _internal_names = pd.DataFrame._internal_names + ['base_class_view']
    _internal_names_set = set(_internal_names)

    def __repr__(self) -> str:
        return self.base_class_view.__repr__()

    @property
    def _constructor(self) -> Callable[..., "BaseDataFrame"]:
        # by default, use the customized class as a constructor, i.e. all
        # classes that inherit from this base class will always use themselves
        # as a constructor
        return self.__class__

    @final
    @property
    def _constructor_sliced(self) -> Callable[..., pd.Series]:
        # dynamically create a subclass of _BaseSeriesConstructor that
        # has a reference to this self (i.e. the object from which the slice
        # is created) as a class property
        # type(...) returns a new subclass of a Series
        return type('_DynamicBaseSeriesConstructor',  # noqa: return type
                    (_BaseSeriesConstructor,),
                    {'__meta_created_from': self})

    @property
    def _constructor_sliced_horizontal(self) -> Callable[..., pd.Series]:
        return pd.Series

    @property
    def _constructor_sliced_vertical(self) -> Callable[..., pd.Series]:
        return pd.Series

    @property
    def base_class_view(self) -> pd.DataFrame:
        """For a nicer debugging experience; can view DataFrame through
        this property in various IDEs"""
        return pd.DataFrame(self)


class _BaseSeriesConstructor(pd.Series):
    """
    Base class for an intermediary and dynamically defined constructor
    class that implements horizontal and vertical slicing of Pandas DataFrames
    with different result objects types.

    This class is never seen by the user. It is never fully instantiated
    because it always returns an instance of a class that does not derive
    from this class in its __new__ method.
    """

    __meta_created_from: Optional[BaseDataFrame]

    def __new__(cls, data=None, index=None, *args, **kwargs) -> pd.Series:
        parent = getattr(cls, '__meta_created_from', None)

        if ((index is None) and isinstance(data, (pd.Series,
                                                  pd.DataFrame,
                                                  SingleBlockManager))):
            # no index is explicitly given, try to get an index from the
            # data itself
            index = getattr(data, 'index', None)

        if (parent is None) or (index is None):
            # do "conventional" slicing and return a pd.Series
            constructor = pd.Series

        elif parent.index is index:
            # our index matches the parent index, therefore, the data is
            # a column of the parent DataFrame
            constructor = parent._constructor_sliced_vertical
        else:
            # the data is a row of the parent DataFrame
            constructor = parent._constructor_sliced_horizontal

        if (isinstance(data, SingleBlockManager)
                and hasattr(constructor, '_from_mgr')
                and pd.__version__.startswith('2.')):
            obj = constructor._from_mgr(data, axes=data.axes)
        else:
            obj = constructor(data=data, index=index, *args, **kwargs)

        if parent is not None:
            # catch-all fix for some missing __finalize__ calls in Pandas
            # (this is mainly an issue with older versions of Pandas)
            obj.__finalize__(parent)

        return obj


class BaseSeries(pd.Series):
    """Base class for objects that inherit from ``pandas.Series``.

    A same-dimensional slice of an object that inherits from this class will
    be of equivalent type (instead of being a Pandas Series).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _constructor(self) -> Callable[..., pd.Series]:
        return self.__class__
