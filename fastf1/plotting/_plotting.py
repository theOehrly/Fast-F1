import warnings
from typing import Optional

import numpy as np
import pandas as pd


try:
    import matplotlib
    from matplotlib import cycler
    from matplotlib import pyplot as plt
except ImportError:
    warnings.warn("Failed to import optional dependency 'matplotlib'!"
                  "Plotting functionality will be unavailable!",
                  RuntimeWarning)
try:
    import timple
except ImportError:
    warnings.warn("Failed to import optional dependency 'timple'!"
                  "Plotting of timedelta values will be restricted!",
                  RuntimeWarning)

from rapidfuzz import fuzz

from fastf1.logger import get_logger
from fastf1.plotting._constants import (
    LEGACY_DRIVER_COLORS,
    LEGACY_DRIVER_TRANSLATE,
    LEGACY_TEAM_COLORS,
    LEGACY_TEAM_TRANSLATE
)


_logger = get_logger(__package__)


_COLOR_PALETTE: list[str] = ['#FF79C6', '#50FA7B', '#8BE9FD', '#BD93F9',
                             '#FFB86C', '#FF5555', '#F1FA8C']
# The default color palette for matplotlib plot lines in fastf1's color scheme


class __DefaultStringArgType(str):
    pass


__color_scheme_default_arg = __DefaultStringArgType('fastf1')


def setup_mpl(
        mpl_timedelta_support: bool = True,
        color_scheme: Optional[str] = __color_scheme_default_arg,
        misc_mpl_mods: bool = True):
    """Setup matplotlib for use with fastf1.

    This is optional but, at least partly, highly recommended.

    .. deprecated:: 3.4.0

        The optional argument ``misc_mpls_mods`` is deprecated.

    .. deprecated:: 3.4.0

        The default value for ``color_scheme`` will change from ``'fastf1'``
        to ``None``. You should explicitly set the desired value when calling
        this function.


    Parameters:
        mpl_timedelta_support (bool):
            Matplotlib itself offers very limited functionality for plotting
            timedelta values. (Lap times, sector times and other kinds of time
            spans are represented as timedelta.)

            Enabling this option will patch some internal matplotlib functions
            and register converters, formatters and locators for tick
            formatting. The heavy lifting for this is done by an external
            package called 'Timple'. See https://github.com/theOehrly/Timple if
            you wish to customize the tick formatting for timedelta.

        color_scheme (str, None):
            This enables the Fast-F1 color scheme that you can see in all
            example images.
            Valid color scheme names are: ['fastf1', None]

        misc_mpl_mods (bool):
            This argument is deprecated since v3.4.0 and should no longer be
            used.
    """
    if color_scheme is __color_scheme_default_arg:
        warnings.warn(
            "FastF1 will no longer silently modify the default Matplotlib "
            "colors in the future.\nTo remove this warning, explicitly set "
            "`color_scheme=None` or `color_scheme='fastf1'` when calling "
            "`.setup_mpl()`.", FutureWarning
        )

    if misc_mpl_mods:
        warnings.warn(
            "FastF1 will stop modifying the default Matplotlib settings in "
            "the future.\nTo opt-in to the new behaviour and remove this "
            "warning, explicitly set `misc_mpl_mods=False` when calling "
            "`.setup_mpl()`.", FutureWarning
        )

    if mpl_timedelta_support:
        _enable_timple()
    if color_scheme == 'fastf1':
        _enable_fastf1_color_scheme()
    if misc_mpl_mods:
        _enable_misc_mpl_mods()


def driver_color(identifier: str) -> str:
    """
    Get a driver's color from a driver name or abbreviation.

    .. deprecated:: 3.4.0
        This function is deprecated and will be removed in a future version.
        Use :func:`~fastf1.plotting.get_driver_color` instead.

    This function will try to find a matching driver for any identifier string
    that is passed to it. This involves case-insensitive matching and partial
    string matching.

    Example::

        >>> driver_color('charles leclerc')  # doctest: +SKIP
        '#dc0000'
        >>> driver_color('max verstappen')  # doctest: +SKIP
        '#fcd700'
        >>> driver_color('ver')  # doctest: +SKIP
        '#fcd700'
        >>> driver_color('lec')  # doctest: +SKIP
        '#dc0000'

        shortened driver names and typos can be dealt with
        too (within reason)

        >>> driver_color('Max Verst')  # doctest: +SKIP
        '#fcd700'
        >>> driver_color('Charles')  # doctest: +SKIP
        '#dc0000'

    Args:
        identifier (str): Abbreviation or uniquely identifying name of the
            driver.

    Returns:
        str: hex color code
    """
    warnings.warn("The function `driver_color` is deprecated and will be "
                  "removed in a future version. Use "
                  "`fastf1.plotting.get_driver_color` instead.",
                  FutureWarning)

    if identifier.upper() in LEGACY_DRIVER_TRANSLATE:
        # try short team abbreviations first
        return LEGACY_DRIVER_COLORS[
            LEGACY_DRIVER_TRANSLATE[identifier.upper()]
        ]
    else:
        identifier = identifier.lower()

        # check for an exact team name match
        if identifier in LEGACY_DRIVER_COLORS:
            return LEGACY_DRIVER_COLORS[identifier]

        # check for exact partial string match
        for team_name, color in LEGACY_DRIVER_COLORS.items():
            if identifier in team_name:
                return color

        # do fuzzy string matching
        key_ratios = list()
        for existing_key in LEGACY_DRIVER_COLORS:
            ratio = fuzz.ratio(identifier, existing_key)
            key_ratios.append((ratio, existing_key))
        key_ratios.sort(reverse=True)
        if key_ratios[0][0] != 100:
            _logger.warning(
                "Correcting invalid user input "
                 f"'{identifier}' to '{key_ratios[0][1]}'."

            )
        if ((key_ratios[0][0] < 35)
                or (key_ratios[0][0] / key_ratios[1][0] < 1.2)):
            # ensure that the best match has a minimum accuracy (35 out of
            # 100) and that it has a minimum confidence (at least 20% better
            # than second best)
            raise KeyError
        best_matched_key = key_ratios[0][1]
        return LEGACY_DRIVER_COLORS[best_matched_key]


def team_color(identifier: str) -> str:
    """
    Get a team's color from a team name or abbreviation.

    .. deprecated:: 3.4.0
        This function is deprecated and will be removed in a future version.
        Use :func:`~fastf1.plotting.get_team_color` instead.

    This function will try to find a matching team for any identifier string
    that is passed to it. This involves case-insensitive matching and partial
    string matching.

    Example::

        >>> team_color('Red Bull')  # doctest: +SKIP
        '#fcd700'
        >>> team_color('redbull')  # doctest: +SKIP
        '#fcd700'
        >>> team_color('Red')  # doctest: +SKIP
        '#fcd700'
        >>> team_color('RBR')  # doctest: +SKIP
        '#fcd700'

        # shortened team names, included sponsors and typos can be dealt with
        # too (within reason)

        >>> team_color('Mercedes')  # doctest: +SKIP
        '#00d2be'
        >>> team_color('Merc')  # doctest: +SKIP
        '#00d2be'
        >>> team_color('Merecds')  # doctest: +SKIP
        '#00d2be'
        >>> team_color('Mercedes-AMG Petronas F1 Team')  # doctest: +SKIP
        '#00d2be'

    Args:
        identifier (str): Abbreviation or uniquely identifying name of the
            team.

    Returns:
        str: hex color code
    """
    warnings.warn("The function `team_color` is deprecated and will be "
                  "removed in a future version. Use "
                  "`fastf1.plotting.get_team_color` instead.",
                  FutureWarning)

    if identifier.upper() in LEGACY_TEAM_TRANSLATE:
        # try short team abbreviations first
        return LEGACY_TEAM_COLORS[LEGACY_TEAM_TRANSLATE[identifier.upper()]]
    else:
        identifier = identifier.lower()
        # remove common non-unique words
        for word in ('racing', 'team', 'f1', 'scuderia'):
            identifier = identifier.replace(word, "")

        # check for an exact team name match
        if identifier in LEGACY_TEAM_COLORS:
            return LEGACY_TEAM_COLORS[identifier]

        # check for exact partial string match
        for team_name, color in LEGACY_TEAM_COLORS.items():
            if identifier in team_name:
                return color

        # do fuzzy string matching
        key_ratios = list()
        for existing_key in LEGACY_TEAM_COLORS.keys():
            ratio = fuzz.ratio(identifier, existing_key)
            key_ratios.append((ratio, existing_key))
        key_ratios.sort(reverse=True)
        if key_ratios[0][0] != 100:
            _logger.warning(
                "Correcting invalid user input "
                 f"'{identifier}' to '{key_ratios[0][1]}'."

            )
        if ((key_ratios[0][0] < 35)
                or (key_ratios[0][0] / key_ratios[1][0] < 1.2)):
            # ensure that the best match has a minimum accuracy (35 out of
            # 100) and that it has a minimum confidence (at least 20% better
            # than second best)
            raise KeyError
        best_matched_key = key_ratios[0][1]
        return LEGACY_TEAM_COLORS[best_matched_key]


def _enable_timple():
    # use external package timple to patch matplotlib
    # this adds converters, locators and formatters for
    # plotting timedelta values
    tick_formats = [
        "%d %day",
        "%H:00",
        "%H:%m",
        "%M:%s.0",
        "%M:%s.%ms"
    ]
    tmpl = timple.Timple(converter='concise',
                         formatter_args={'show_offset_zero': False,
                                         'formats': tick_formats})
    tmpl.enable()


def _enable_misc_mpl_mods():
    def _bar_sorted(bar):
        def _bar_sorted_decorator(*args, **kwargs):
            if 'edgecolor' not in kwargs:
                kwargs['edgecolor'] = 'none'
            if 'sort' in kwargs and len(val := args[-1]):
                s = kwargs['sort']
                if s == 'increasing' or s == 1:
                    s = False
                if s == 'decreasing' or s == -1:
                    s = True
                _ids = [list(val).index(a) for a in sorted(val, reverse=s)]
                _args = [[args[-2][i] for i in _ids],
                         [args[-1][i] for i in _ids]]
                if len(args) > 2:
                    _args.insert(0, args[0])
                args = _args
                for key in kwargs:
                    if isinstance(kwargs[key], (pd.core.series.Series)):
                        kwargs[key] = kwargs[key].to_numpy()
                    if isinstance(kwargs[key], (list, np.ndarray)):
                        kwargs[key] = [kwargs[key][i] for i in _ids]
                kwargs.pop('sort', None)
            return bar(*args, **kwargs)

        return _bar_sorted_decorator

    plt.bar = _bar_sorted(plt.bar)
    plt.barh = _bar_sorted(plt.barh)
    matplotlib.axes.Axes.bar = _bar_sorted(matplotlib.axes.Axes.bar)
    matplotlib.axes.Axes.barh = _bar_sorted(matplotlib.axes.Axes.barh)

    def _nice_grid(ax):
        if isinstance(ax, np.ndarray):
            [_nice_grid(_ax) for _ax in ax]
        else:
            ax.minorticks_on()
            grid = getattr(ax, 'grid')
            grid(visible=True, which='major', color='#4f4845',
                 linestyle='-', linewidth=1)
            grid(visible=True, which='minor', color='#3f3a38',
                 linestyle='--', linewidth=0.5)

    _subplots_placeholder = plt.subplots

    def _subplots(*args, **kwargs):
        fig, ax = _subplots_placeholder(*args, **kwargs)
        _nice_grid(ax)
        return fig, ax

    plt.subplots = _subplots

    _savefig_placeholder = matplotlib.figure.Figure.savefig

    def _save(*args, **kwargs):
        if 'facecolor' not in kwargs:
            kwargs['facecolor'] = args[0].get_facecolor()
        if 'edgecolors' not in kwargs:
            kwargs['edgecolor'] = 'none'
        return _savefig_placeholder(*args, **kwargs)

    matplotlib.figure.Figure.savefig = _save


def _enable_fastf1_color_scheme():
    plt.rcParams['figure.facecolor'] = '#292625'
    plt.rcParams['axes.edgecolor'] = '#2d2928'
    plt.rcParams['xtick.color'] = '#f1f2f3'
    plt.rcParams['ytick.color'] = '#f1f2f3'
    plt.rcParams['axes.labelcolor'] = '#F1f2f3'
    plt.rcParams['axes.facecolor'] = '#1e1c1b'
    # plt.rcParams['axes.facecolor'] = '#292625'
    plt.rcParams['axes.titlesize'] = 'x-large'
    # plt.rcParams['font.family'] = 'Gravity'
    plt.rcParams['font.weight'] = 'medium'
    plt.rcParams['text.color'] = '#F1F1F3'
    plt.rcParams['axes.titlesize'] = '19'
    plt.rcParams['axes.titlepad'] = '12'
    plt.rcParams['axes.titleweight'] = 'light'
    plt.rcParams['axes.prop_cycle'] = cycler('color', _COLOR_PALETTE)
    plt.rcParams['legend.fancybox'] = False
    plt.rcParams['legend.facecolor'] = (0.1, 0.1, 0.1, 0.7)
    plt.rcParams['legend.edgecolor'] = (0.1, 0.1, 0.1, 0.9)
    plt.rcParams['savefig.transparent'] = False
    plt.rcParams['axes.axisbelow'] = True


def lapnumber_axis(ax, axis='xaxis'):
    """
    Set axis to integer ticks only.

    .. deprecated:: 3.4.0
        The function ``lapnumber_axis`` is deprecated and will be removed in a
        future version without replacement.

    Args:
        ax: matplotlib axis
        axis: can be 'xaxis' or 'yaxis'

    Returns:
        the modified axis instance
    """
    warnings.warn("The function `lapnumber_axis` is deprecated and will be "
                  "removed without replacement in a future version.",
                  FutureWarning)
    getattr(ax, axis).get_major_locator().set_params(integer=True,
                                                     min_n_ticks=0)

    return ax
