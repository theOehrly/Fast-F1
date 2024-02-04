import warnings
from functools import cached_property
from typing import (
    Dict,
    List
)

from fastf1.core import Session
from fastf1.plotting._constants import LEGACY_TEAM_TRANSLATE as _LGT
from fastf1.plotting._constants import Constants as _Constants
from fastf1.plotting._constants.base import Colormaps as _Colormaps
from fastf1.plotting._constants.base import Compounds as _Compounds
from fastf1.plotting._drivers import (  # noqa: F401
    _get_driver_team_mapping,
    add_sorted_driver_legend,
    get_driver_abbreviation,
    get_driver_abbreviations_by_team,
    get_driver_color,
    get_driver_name,
    get_driver_names_by_team,
    get_driver_style,
    get_team_color,
    get_team_name,
    get_team_name_by_driver
)
from fastf1.plotting._plotting import (  # noqa: F401
    _COLOR_PALETTE,
    driver_color,
    setup_mpl,
    team_color
)


def __getattr__(name):
    if name in ('COMPOUND_COLORS', 'DRIVER_TRANSLATE',
                'TEAM_COLORS', 'TEAM_TRANSLATE', 'COLOR_PALETTE'):
        warnings.warn(f"{name} is deprecated and will be removed in a future"
                      f"version.", FutureWarning)
        return globals()[f"_DEPR_{name}"]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_DEPR_COMPOUND_COLORS: Dict[str, str] = {
    str(key.value): val for key, val
    in _Constants['2024'].CompoundColors.items()
}
COMPOUND_COLORS: Dict[str, str]
"""
Mapping of tyre compound names to compound colors (hex color codes).
(current season only)

.. deprecated:: 3.3.0
    The ``COMPOUND_COLORS`` dictionary is deprecated and will be removed in a
    future version. Use :func:`~fastf1.plotting.get_compound_color` instead.
"""

@cached_property
def _DEPR_DRIVER_TRANSLATE() -> Dict[str, str]:
    dtm = _get_driver_team_mapping(session=None)
    abb_to_name = dtm.abbreviation_to_name
    for abb in abb_to_name.keys():
        abb_to_name[abb] = abb_to_name[abb].lower()
    return abb_to_name


DRIVER_TRANSLATE: Dict[str, str]
"""
Mapping of driver names to theirs respective abbreviations.

.. deprecated:: 3.3.0
    The ``DRIVER_TRANSLATE`` dictionary is deprecated and will be removed in a
    future version. Use :func:`~fastf1.plotting.get_driver_name` instead.
"""

_DEPR_TEAM_COLORS: Dict[str, str] = {
    str(key.value): val for key, val
    in _Constants['2024'].Colormaps[_Colormaps.Default].items()
}
TEAM_COLORS: Dict[str, str]
"""
Mapping of team names to team colors (hex color codes).
(current season only)

.. deprecated:: 3.3.0
    The ``TEAM_COLORS`` dictionary is deprecated and will be removed in a
    future version. Use :func:`~fastf1.plotting.get_team_color` instead.
"""

_DEPR_TEAM_TRANSLATE: Dict[str, str] = {
    str(key): val for key, val in _LGT.items()
}
TEAM_TRANSLATE: Dict[str, str]
"""
Mapping of team names to theirs respective abbreviations.

.. deprecated:: 3.3.0
    The ``TEAM_TRANSLATE`` dictionary is deprecated and will be removed in a
    future version. Use :func:`~fastf1.plotting.get_team_name` instead.
"""

_DEPR_COLOR_PALETTE: List[str] = _COLOR_PALETTE.copy()
COLOR_PALETTE: Dict[str, str]
"""
The default color palette for matplotlib plot lines in fastf1's color scheme.

.. deprecated:: 3.3.0
    The ``COLOR_PALETTE`` list is deprecated and will be removed in a
    future version with no replacement.
"""


def get_compound_color(compound: str, *, session: Session) -> str:
    """
    Get the compound color as hexadecimal RGB color code for a given compound.

    Args:
        compound: The name of the compound
        session: the session for which the data should be obtained

    Returns: A hexadecimal RGB color code
    """
    year = str(session.event['EventDate'].year)
    return _Constants[year].CompoundColors[_Compounds(compound.upper())]
