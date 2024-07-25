import warnings

from fastf1.plotting._constants import \
    LEGACY_DRIVER_COLORS as _LEGACY_DRIVER_COLORS
from fastf1.plotting._constants import \
    LEGACY_DRIVER_TRANSLATE as _LEGACY_DRIVER_TRANSLATE
from fastf1.plotting._constants import \
    LEGACY_TEAM_TRANSLATE as _LEGACY_TEAM_TRANSLATE
from fastf1.plotting._constants import Constants as _Constants
from fastf1.plotting._interface import (  # noqa: F401
    _get_driver_team_mapping,
    add_sorted_driver_legend,
    get_compound_color,
    get_compound_mapping,
    get_driver_abbreviation,
    get_driver_abbreviations_by_team,
    get_driver_color,
    get_driver_color_mapping,
    get_driver_name,
    get_driver_names_by_team,
    get_driver_style,
    get_team_color,
    get_team_name,
    get_team_name_by_driver,
    list_compounds,
    list_driver_abbreviations,
    list_driver_names,
    list_team_names,
    override_team_constants,
    set_default_colormap
)
from fastf1.plotting._plotting import (  # noqa: F401
    _COLOR_PALETTE,
    driver_color,
    lapnumber_axis,
    setup_mpl,
    team_color
)


__all__ = [
    # imported, current
    'add_sorted_driver_legend',
    'get_compound_color',
    'get_compound_mapping',
    'get_driver_abbreviation',
    'get_driver_abbreviations_by_team',
    'get_driver_color',
    'get_driver_color_mapping',
    'get_driver_name',
    'get_driver_names_by_team',
    'get_driver_style',
    'get_team_color',
    'get_team_name',
    'get_team_name_by_driver',
    'list_compounds',
    'list_driver_abbreviations',
    'list_driver_names',
    'list_team_names',
    'override_team_constants',
    'set_default_colormap',
    'setup_mpl',

    # imported, legacy
    'driver_color',
    'lapnumber_axis',
    'team_color',

    # legacy
    'COMPOUND_COLORS',
    'DRIVER_COLORS',
    'DRIVER_TRANSLATE',
    'TEAM_COLORS',
    'TEAM_TRANSLATE',
    'COLOR_PALETTE'
]


def __getattr__(name):
    if name in ('COMPOUND_COLORS', 'DRIVER_TRANSLATE', 'DRIVER_COLORS',
                'TEAM_COLORS', 'TEAM_TRANSLATE', 'COLOR_PALETTE'):
        warnings.warn(f"{name} is deprecated and will be removed in a future "
                      f"version.", FutureWarning)

        return globals()[f"_DEPR_{name}"]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_DEPR_COMPOUND_COLORS: dict[str, str] = {
    key: val for key, val
    in _Constants['2024'].CompoundColors.items()
}
COMPOUND_COLORS: dict[str, str]
"""
Mapping of tyre compound names to compound colors (hex color codes).
(current season only)

.. deprecated:: 3.4.0
    The ``COMPOUND_COLORS`` dictionary is deprecated and will be removed in a
    future version. Use :func:`~fastf1.plotting.get_compound_color` or
    :func:`~fastf1.plotting.get_compound_mapping` instead.
"""


_DEPR_DRIVER_COLORS: dict[str, str] = _LEGACY_DRIVER_COLORS.copy()
DRIVER_COLORS: dict[str, str]
"""
Mapping of driver names to driver colors (hex color codes).

.. warning::
    This dictionary will no longer be updated to include new drivers. Use
    the new API instead.

.. deprecated:: 3.4.0
    The ``DRIVER_COLORS`` dictionary is deprecated and will ber removed in a
    future version. Use :func:`~fastf1.plotting.get_driver_color` or
    :func:`~fastf1.plotting.get_driver_color_mapping` instead.
"""


_DEPR_DRIVER_TRANSLATE: dict[str, str] = _LEGACY_DRIVER_TRANSLATE.copy()
DRIVER_TRANSLATE: dict[str, str]
"""
Mapping of driver names to theirs respective abbreviations.

.. warning::
    This dictionary will no longer be updated to include new drivers. Use
    the new API instead.


.. deprecated:: 3.4.0
    The ``DRIVER_TRANSLATE`` dictionary is deprecated and will be removed in a
    future version. Use :func:`~fastf1.plotting.get_driver_name` instead.
"""

_DEPR_TEAM_COLORS: dict[str, str] = {
    # str(key.value): val for key, val
    # in _Constants['2024'].Colormaps[_Colormaps.Default].items()
    name.replace("kick ", ""): team.TeamColor.FastF1 for name, team
    in _Constants['2024'].Teams.items()
}
TEAM_COLORS: dict[str, str]
"""
Mapping of team names to team colors (hex color codes).
(current season only)

.. deprecated:: 3.4.0
    The ``TEAM_COLORS`` dictionary is deprecated and will be removed in a
    future version. Use :func:`~fastf1.plotting.get_team_color` instead.
"""

_DEPR_TEAM_TRANSLATE: dict[str, str] = _LEGACY_TEAM_TRANSLATE.copy()
TEAM_TRANSLATE: dict[str, str]
"""
Mapping of team names to theirs respective abbreviations.

.. deprecated:: 3.4.0
    The ``TEAM_TRANSLATE`` dictionary is deprecated and will be removed in a
    future version. Use :func:`~fastf1.plotting.get_team_name` instead.
"""

_DEPR_COLOR_PALETTE: list[str] = _COLOR_PALETTE.copy()
COLOR_PALETTE: list[str]
"""
The default color palette for matplotlib plot lines in fastf1's color scheme.

.. deprecated:: 3.4.0
    The ``COLOR_PALETTE`` list is deprecated and will be removed in a
    future version with no replacement.
"""
