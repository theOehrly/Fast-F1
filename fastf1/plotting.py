"""
:mod:`fastf1.plotting` - Plotting module
========================================

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


TEAM_COLORS = {'Mercedes': '#00d2be', 'Ferrari': '#dc0000',
               'Red Bull': '#0600ef', 'McLaren': '#ff8700',
               'Alpine F1 Team': '#0090ff', 'Aston Martin': '#006f62',
               'Alfa Romeo': '#900000', 'AlphaTauri': '#2b4562',
               'Haas F1 Team': '#ffffff', 'Williams': '#005aff'}
"""Mapping of team colors (hex color code) to team names.
(current season only)"""

TEAM_TRANSLATE = {'MER': 'Mercedes', 'FER': 'Ferrari',
                  'RBR': 'Red Bull', 'MCL': 'McLaren',
                  'APN': 'Alpine F1 Team', 'AMR': 'Aston Martin',
                  'ARR': 'Alfa Romeo', 'APT': 'AlphaTauri',
                  'HAA': 'Haas F1 Team', 'WIL': 'Williams'}
"""Mapping of team names to theirs respective abbreviations."""

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


def team_color(identifier):
    """Get a teams color.

    Args:
        identifier (str): Abbreviation or full name of the team.
            For example "RBR" or "Red Bull" would both return the same result.

    Returns:
        str: hex color code
    """
    if identifier in TEAM_COLORS.keys():
        return TEAM_COLORS[identifier]
    elif identifier in TEAM_TRANSLATE:
        return TEAM_COLORS[TEAM_TRANSLATE[identifier]]
    else:
        return None


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
            grid(b=True, which='major', color='#4f4845', linestyle='-', linewidth=1)
            grid(b=True, which='minor', color='#3f3a38', linestyle='--', linewidth=0.5)

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
