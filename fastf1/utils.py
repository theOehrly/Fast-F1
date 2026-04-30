"""Deprecated public helpers.

The functions in this module were never intended to be part of the public
API; see issue #884 for more details. They remain importable for backwards
compatibility but emit a :class:`DeprecationWarning` and forward to the
implementations in :mod:`fastf1._utils`. They will be removed in a future
release.
"""
import datetime
import warnings

from fastf1._utils import recursive_dict_get as _recursive_dict_get
from fastf1._utils import to_datetime as _to_datetime
from fastf1._utils import to_timedelta as _to_timedelta


_DEPRECATION_MSG = (
    "`fastf1.utils.{name}` was never intended to be part of the public API "
    "and is deprecated. It will be removed in a future release."
)


def recursive_dict_get(d: dict, *keys: str, default_none: bool = False):
    """Recursive dict get. Can take an arbitrary number of keys and returns an
    empty dict if any key does not exist.
    https://stackoverflow.com/a/28225747

    .. deprecated:: 3.9.0
        This function was never intended to be part of the public API and
        will be removed in a future release.
    """
    warnings.warn(
        _DEPRECATION_MSG.format(name="recursive_dict_get"),
        DeprecationWarning,
        stacklevel=2,
    )
    return _recursive_dict_get(d, *keys, default_none=default_none)


def to_timedelta(x: str | datetime.timedelta) \
        -> datetime.timedelta | None:
    """Fast timedelta object creation from a time string

    Permissible string formats:

        For example: `13:24:46.320215` with:

            - optional hours and minutes
            - optional microseconds and milliseconds with
              arbitrary precision (1 to 6 digits)

        Examples of valid formats:

            - `24.3564` (seconds + milli/microseconds)
            - `36:54` (minutes + seconds)
            - `8:45:46` (hours, minutes, seconds)

    Args:
        x: timestamp

    .. deprecated:: 3.9.0
        This function was never intended to be part of the public API and
        will be removed in a future release.
    """
    warnings.warn(
        _DEPRECATION_MSG.format(name="to_timedelta"),
        DeprecationWarning,
        stacklevel=2,
    )
    return _to_timedelta(x)


def to_datetime(x: str | datetime.datetime) \
        -> datetime.datetime | None:
    """Fast datetime object creation from a date string.

    Permissible string formats:

        For example '2020-12-13T13:27:15.320000Z' with:

            - optional milliseconds and microseconds with
              arbitrary precision (1 to 6 digits)
            - with optional trailing letter 'Z'

        Examples of valid formats:

            - `2020-12-13T13:27:15.320000`
            - `2020-12-13T13:27:15.32Z`
            - `2020-12-13T13:27:15`

    Args:
        x: timestamp

    .. deprecated:: 3.9.0
        This function was never intended to be part of the public API and
        will be removed in a future release.
    """
    warnings.warn(
        _DEPRECATION_MSG.format(name="to_datetime"),
        DeprecationWarning,
        stacklevel=2,
    )
    return _to_datetime(x)
