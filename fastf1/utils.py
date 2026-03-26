"""
DEPRECATED: This module is being removed.
"""

import warnings
from typing import Any, Dict, List, Optional
import pandas as pd

from fastf1._utils import _recursive_dict_get, _to_datetime, _to_timedelta


def recursive_dict_get(d: Dict, keys: List[str]) -> Optional[Any]:
    """DEPRECATED - use _recursive_dict_get instead."""
    warnings.warn(
        "recursive_dict_get is deprecated and will be removed in version 4.0.",
        DeprecationWarning,
        stacklevel=2
    )
    return _recursive_dict_get(d, keys)


def to_datetime(value: Any) -> Optional[pd.Timestamp]:
    """DEPRECATED - use _to_datetime instead."""
    warnings.warn(
        "to_datetime is deprecated and will be removed in version 4.0.",
        DeprecationWarning,
        stacklevel=2
    )
    return _to_datetime(value)


def to_timedelta(value: Any) -> Optional[pd.Timedelta]:
    """DEPRECATED - use _to_timedelta instead."""
    warnings.warn(
        "to_timedelta is deprecated and will be removed in version 4.0.",
        DeprecationWarning,
        stacklevel=2
    )
    return _to_timedelta(value)


def delta_time(*args, **kwargs):
    """REMOVED - this function is no longer available."""
    raise AttributeError(
        "delta_time has been removed because it was inaccurate."
    )