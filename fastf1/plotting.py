"""
Plotting - :mod:`fastf1.plotting`
=================================

Helper functions for creating data plots.

:mod:`fastf1.plotting` provides optional functionality with the intention of making
it easy to create nice plots.

This module offers mainly two things:
    - team names and colors
    - matplotlib mods and helper functions

Fast-F1 focuses on plotting data with matplotlib. Of course, you are not
required to use matplotlib and you can use any other tool you like.

If you wish to use matplotlib, it is highly recommended to enable some
helper functions by calling :func:`setup_mpl`.

If you don't want to use matplotlib, you can still use the team names
and colors which are provided below.


.. note:: Plotting related functionality is likely to change in a future
    release.
"""

import pandas as pd
import numpy as np
import warnings

try:
    import matplotlib
    from matplotlib import pyplot as plt
    from matplotlib import cycler
except ImportError:
    warnings.warn("Failed to import optional dependency 'matplotlib'!"
                  "Plotting functionality will be unavailable!", UserWarning)
try:
    import timple
except ImportError:
    warnings.warn("Failed to import optional dependency 'timple'!"
                  "Plotting of timedelta values will be restricted!",
                  UserWarning)

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', message="Using slow pure-python SequenceMatcher")
    # suppress that warning, it's confusing at best here, we don't need fast sequence matching
    # and the installation (on windows) some effort
    from thefuzz import fuzz


class __TeamColorsWarnDict(dict):
    """Implements userwarning on KeyError in :any:`TEAM_COLORS` after
    changing team names."""
    def get(self, key, default=None):
        value = super().get(key, default)
        if value is None:
            self.warn_change()
        return value

    def __getitem__(self, item):
        try:
            return super().__getitem__(item)
        except KeyError as err:
            self.warn_change()
            raise err
        except Exception as err:
            raise err

    def warn_change(self):
        warnings.warn(
            "Team names in `TEAM_COLORS` are now lower-case and only contain "
            "the most identifying part of the name. "
            "Use function `.team_color` alternatively.", UserWarning
        )


TEAM_COLORS = __TeamColorsWarnDict({
    'mercedes': '#00d2be', 'ferrari': '#dc0000',
    'red bull': '#0600ef', 'mclaren': '#ff8700',
    'alpine': '#0090ff', 'aston martin': '#006f62',
    'alfa romeo': '#900000', 'alphatauri': '#2b4562',
    'haas': '#ffffff', 'williams': '#005aff'
})
"""Mapping of team colors (hex color code) to team names.
(current season only)"""


TEAM_TRANSLATE = {'MER': 'mercedes', 'FER': 'ferrari',
                  'RBR': 'red bull', 'MCL': 'mclaren',
                  'APN': 'alpine', 'AMR': 'aston martin',
                  'ARR': 'alfa romeo', 'APT': 'alphatauri',
                  'HAA': 'haas', 'WIL': 'williams'}
"""Mapping of team names to theirs respective abbreviations."""

DRIVER_COLORS = {
        "valtteri bottas": "#900000",
        "zhou guanyu": "#500000",

        "pierre gasly": "#2b4562",
        "yuki tsunoda": "#356cac",

        "fernando alonso": "#0090ff",
        "esteban ocon": "#70c2ff",

        "sebastian vettel": "#006f62",
        "lance stroll": "#25a617",
        "nico hulkenberg": "#2f9b90",

        "charles leclerc": "#dc0000",
        "carlos sainz": "#ff8181",

        "kevin magnussen": "#ffffff",
        "mick schumacher": "#cacaca",

        "daniel ricciardo": "#ff8700",
        "lando norris": "#eeb370",

        "lewis hamilton": "#00d2be",
        "george russell": "#24ffff",

        "max verstappen": "#0600ef",
        "sergio perez": "#716de2",

        "alexander albon": "#005aff",
        "nicholas latifi": "#012564",
    }
"""Mapping of driver colors (hex color code) to driver names.
(current season only)"""


DRIVER_TRANSLATE = {'LEC': 'charles leclerc', 'SAI': 'carlos sainz',
                    'VER': 'max verstappen', 'SER': 'sergio perez',
                    'RIC': 'daniel ricciardo', 'NOR': 'lando norris',
                    'ALO': 'fernando alonso', 'OCO': 'esteban ocon',
                    'BOT': 'valtteri bottas', 'ZHO': 'zhou guanyu',
                    'GAS': 'pierre gasly', 'TSU': 'yuki tsunoda',
                    'MAG': 'kevin magnussen', 'MSC': 'mick schumacher',
                    'VET': 'sebastian vettel', 'HUL': 'nico hulkenberg',
                    'STR': 'lance stroll',
                    'HAM': 'lewis hamilton', 'RUS': 'george russell',
                    'ALB': 'alexander albon', 'LAT': 'nicholas latifi'}
"""Mapping of driver names to theirs respective abbreviations."""

COLOR_PALETTE = ['#FF79C6', '#50FA7B', '#8BE9FD', '#BD93F9',
                 '#FFB86C', '#FF5555', '#F1FA8C']
"""The default color palette for matplotlib plot lines in fastf1's color
scheme."""


def setup_mpl(mpl_timedelta_support=True, color_scheme='fastf1',
              misc_mpl_mods=True):
    """Setup matplotlib for use with fastf1.

    This is optional but, at least partly, highly recommended.

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
            This enables the Fast-F1 color scheme that you can see in all example
            images.
            Valid color scheme names are: ['fastf1', None]

        misc_mpl_mods (bool):
            This enables a collection of patches for the following mpl features:

                - ``.savefig`` (saving of figures)
                - ``.bar``/``.barh`` (plotting of bar graphs)
                - ``plt.subplots`` (for creating a nice background grid)
    """
    if mpl_timedelta_support:
        _enable_timple()
    if color_scheme == 'fastf1':
        _enable_fastf1_color_scheme()
    if misc_mpl_mods:
        _enable_misc_mpl_mods()


def driver_color(identifier):
    """Get a driver's color from a driver name or abbreviation.

    This function will try to find a matching driver for any identifier string
    that is passed to it. This involves case insensitive matching and partial
    string matching.

    If you want exact string matching, you should use the
    :any:`DRIVER_COLORS` dictionary directly, using :any:`DRIVER_TRANSLATE` to
    convert abbreviations to team names if necessary.

    Example::

        >>> driver_color('charles leclerc')
        '#dc0000'
        >>> driver_color('max verstappen')
        '#0600ef'
        >>> driver_color('ver')
        '#0600ef'
        >>> driver_color('lec')
        '#dc0000'

        shortened driver names and typos can be dealt with
        too (within reason)

        >>> driver_color('Max Verst')
        '#0600ef'
        >>> driver_color('Charles')
        '#dc0000'

    Args:
        identifier (str): Abbreviation or uniquely identifying name of the driver.

    Returns:
        str: hex color code
    """

    if identifier.upper() in DRIVER_TRANSLATE:
        # try short team abbreviations first
        return DRIVER_COLORS[DRIVER_TRANSLATE[identifier.upper()]]
    else:
        identifier = identifier.lower()

        # check for an exact team name match
        if identifier in DRIVER_COLORS:
            return DRIVER_COLORS[identifier]

        # check for exact partial string match
        for team_name, color in DRIVER_COLORS.items():
            if identifier in team_name:
                return color

        # do fuzzy string matching
        key_ratios = list()
        for existing_key in DRIVER_COLORS.keys():
            ratio = fuzz.ratio(identifier, existing_key)
            key_ratios.append((ratio, existing_key))
        key_ratios.sort(reverse=True)
        if (key_ratios[0][0] < 35) or (key_ratios[0][0]/key_ratios[1][0] < 1.2):
            # ensure that the best match has a minimum accuracy (35 out of
            # 100) and that it has a minimum confidence (at least 20% better
            # than second best)
            raise KeyError
        best_matched_key = key_ratios[0][1]
        return DRIVER_COLORS[best_matched_key]


def team_color(identifier):
    """Get a team's color from a team name or abbreviation.

    This function will try to find a matching team for any identifier string
    that is passed to it. This involves case insensitive matching and partial
    string matching.

    If you want exact string matching, you should use the
    :any:`TEAM_COLORS` dictionary directly, using :any:`TEAM_TRANSLATE` to
    convert abbreviations to team names if necessary.

    Example::

        >>> team_color('Red Bull')
        '#0600ef'
        >>> team_color('redbull')
        '#0600ef'
        >>> team_color('Red')
        '#0600ef'
        >>> team_color('RBR')
        '#0600ef'

        shortened team names, included sponsors and typos can be dealt with
        too (within reason)

        >>> team_color('Mercedes')
        '#00d2be'
        >>> team_color('Merc')
        '#00d2be'
        >>> team_color('Merecds')
        '#00d2be'
        >>> team_color('Mercedes-AMG Petronas F1 Team')
        '#00d2be'

    Args:
        identifier (str): Abbreviation or uniquely identifying name of the team.

    Returns:
        str: hex color code
    """
    if identifier.upper() in TEAM_TRANSLATE:
        # try short team abbreviations first
        return TEAM_COLORS[TEAM_TRANSLATE[identifier.upper()]]
    else:
        identifier = identifier.lower()
        # remove common non-unique words
        for word in ('racing', 'team', 'f1', 'scuderia'):
            identifier = identifier.replace(word, "")

        # check for an exact team name match
        if identifier in TEAM_COLORS:
            return TEAM_COLORS[identifier]

        # check for exact partial string match
        for team_name, color in TEAM_COLORS.items():
            if identifier in team_name:
                return color

        # do fuzzy string matching
        key_ratios = list()
        for existing_key in TEAM_COLORS.keys():
            ratio = fuzz.ratio(identifier, existing_key)
            key_ratios.append((ratio, existing_key))
        key_ratios.sort(reverse=True)
        if (key_ratios[0][0] < 35) or (key_ratios[0][0]/key_ratios[1][0] < 1.2):
            # ensure that the best match has a minimum accuracy (35 out of
            # 100) and that it has a minimum confidence (at least 20% better
            # than second best)
            raise KeyError
        best_matched_key = key_ratios[0][1]
        return TEAM_COLORS[best_matched_key]


def lapnumber_axis(ax, axis='xaxis'):
    """Set axis to integer ticks only."

    Args:
        ax: matplotlib axis
        axis (='xaxis', optional): can be 'xaxis' or 'yaxis'

    Returns:
        the modified axis instance

    """
    getattr(ax, axis).get_major_locator().set_params(integer=True, min_n_ticks=0)

    return ax


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
    plt.rcParams['axes.prop_cycle'] = cycler('color', COLOR_PALETTE)
    plt.rcParams['legend.fancybox'] = False
    plt.rcParams['legend.facecolor'] = (0.1, 0.1, 0.1, 0.7)
    plt.rcParams['legend.edgecolor'] = (0.1, 0.1, 0.1, 0.9)
    plt.rcParams['savefig.transparent'] = False
    plt.rcParams['axes.axisbelow'] = True
