import warnings
from typing import Optional


try:
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

from fastf1.logger import get_logger


_logger = get_logger(__package__)


_COLOR_PALETTE: list[str] = ['#FF79C6', '#50FA7B', '#8BE9FD', '#BD93F9',
                             '#FFB86C', '#FF5555', '#F1FA8C']
# The default color palette for matplotlib plot lines in fastf1's color scheme


def setup_mpl(
        mpl_timedelta_support: bool = True,
        color_scheme: Optional[str] = None,
        *args, **kwargs  # for backwards compatibility, do not use in new code
):
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
            This enables the Fast-F1 color scheme that you can see in all
            example images.
            Valid color scheme names are: ['fastf1', None]
    """
    if args or 'misc_mpl_mods' in kwargs:
        warnings.warn(
            "The `misc_mpl_mods` argument was dropped from `.setup_mpl()` in "
            "version 3.6.0 and has no effect anymore. It will be removed in a "
            "future version of FastF1.", FutureWarning
        )

    if mpl_timedelta_support:
        _enable_timple()
    if color_scheme == 'fastf1':
        _enable_fastf1_color_scheme()


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
