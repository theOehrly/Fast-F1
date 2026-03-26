
"""
Private utilities for Fast-F1 internal use only.
"""

import warnings
import pandas as pd
from typing import Any, Dict, List, Optional


def _recursive_dict_get(d: Dict, keys: List[str]) -> Optional[Any]:
    """Get value from nested dictionary."""
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
            if d is None:
                return None
        else:
            return None
    return d


def _to_datetime(value: Any) -> Optional[pd.Timestamp]:
    """Convert to datetime."""
    if value is None:
        return None
    try:
        return pd.to_datetime(value)
    except (ValueError, TypeError):
        return None


def _to_timedelta(value: Any) -> Optional[pd.Timedelta]:
    """Convert to timedelta."""
    if value is None:
        return None
    try:
        return pd.to_timedelta(value)
    except (ValueError, TypeError):
        return None