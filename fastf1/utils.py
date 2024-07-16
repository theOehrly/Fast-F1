"""This is a collection of various functions."""
import datetime
import warnings
from functools import reduce
from typing import (
    Optional,
    Union
)

import numpy as np
import pandas as pd

import fastf1
from fastf1.logger import get_logger


_logger = get_logger(__name__)


def delta_time(
        reference_lap: "fastf1.core.Lap",
        compare_lap: "fastf1.core.Lap"
) -> tuple[pd.Series, "fastf1.core.Telemetry", "fastf1.core.Telemetry"]:
    """Calculates the delta time of a given lap, along the 'Distance' axis
    of the reference lap.

    .. deprecated:: 3.0.0

    .. warning:: This function should no longer be considered as a stable part
        of the API. Due to the reasons given below, this function will be
        modified or removed at a future point.

    .. warning:: This is a nice gimmick but not actually very accurate which
        is an inherent problem from the way this is calculated currently
        (There may not be a better way though). In comparison with the sector
        times and the differences that can be calculated from these, there are
        notable differences! You should always verify the result against
        sector time differences or find a different way for verification.

    Here is an example that compares the quickest laps of Leclerc and
    Hamilton from Bahrain 2021 Qualifying:

    .. plot::
        :include-source:

        import fastf1 as ff1
        from fastf1 import plotting
        from fastf1 import utils
        from matplotlib import pyplot as plt

        plotting.setup_mpl(misc_mpl_mods=False, color_scheme='fastf1')

        session = ff1.get_session(2021, 'Emilia Romagna', 'Q')
        session.load()
        lec = session.laps.pick_driver('LEC').pick_fastest()
        ham = session.laps.pick_driver('HAM').pick_fastest()

        delta_time, ref_tel, compare_tel = utils.delta_time(ham, lec)
        # ham is reference, lec is compared

        fig, ax = plt.subplots()
        # use telemetry returned by .delta_time for best accuracy,
        # this ensures the same applied interpolation and resampling
        ax.plot(ref_tel['Distance'], ref_tel['Speed'],
                color=plotting.get_team_color(ham['Team'], session))
        ax.plot(compare_tel['Distance'], compare_tel['Speed'],
                color=plotting.get_team_color(lec['Team'], session))

        twin = ax.twinx()
        twin.plot(ref_tel['Distance'], delta_time, '--', color='white')
        twin.set_ylabel("<-- Lec ahead | Ham ahead -->")
        plt.show()

    Args:
        reference_lap: The lap taken as reference
        compare_lap: The lap to compare

    Returns:
        A tuple containing

        - pd.Series of type `float64` with the delta in seconds.
        - :class:`~fastf1.core.Telemetry` for the reference lap
        - :class:`~fastf1.core.Telemetry` for the comparison lap

        Use the return telemetry for plotting to make sure you have
        telemetry data that was created with the same interpolation and
        resampling options!
    """
    warnings.warn("`utils.delta_time` is considered deprecated and will"
                  "be modified or removed in a future release because it has"
                  "a tendency to give inaccurate results.",
                  FutureWarning)

    ref = reference_lap.get_car_data(interpolate_edges=True).add_distance()
    comp = compare_lap.get_car_data(interpolate_edges=True).add_distance()

    def mini_pro(stream):
        # Ensure that all samples are interpolated
        dstream_start = stream[1] - stream[0]
        dstream_end = stream[-1] - stream[-2]
        return np.concatenate(
            [[stream[0] - dstream_start], stream, [stream[-1] + dstream_end]]
        )

    ltime = mini_pro(comp['Time'].dt.total_seconds().to_numpy())
    multiplier = ref.Distance.iat[-1]/comp.Distance.iat[-1]
    ldistance = mini_pro(comp['Distance'].to_numpy())*multiplier
    lap_time = np.interp(ref['Distance'], ldistance, ltime)

    delta = lap_time - ref['Time'].dt.total_seconds()

    return delta, ref, comp


def recursive_dict_get(d: dict, *keys: str, default_none: bool = False):
    """Recursive dict get. Can take an arbitrary number of keys and returns an
    empty dict if any key does not exist.
    https://stackoverflow.com/a/28225747"""
    ret = reduce(lambda c, k: c.get(k, {}), keys, d)
    if default_none and ret == {}:
        return None
    else:
        return ret


def to_timedelta(x: Union[str, datetime.timedelta]) \
        -> Optional[datetime.timedelta]:
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
    """
    # this is faster than using pd.timedelta on a string
    if isinstance(x, str) and len(x):
        try:
            hours, minutes = 0, 0
            if len(hms := x.split(':')) == 3:
                hours, minutes, seconds = hms
            elif len(hms) == 2:
                minutes, seconds = hms
            else:
                seconds = hms[0]

            if '.' in seconds:
                seconds, msus = seconds.split('.')
                if len(msus) < 6:
                    msus = msus + '0' * (6 - len(msus))
                elif len(msus) > 6:
                    msus = msus[0:6]
            else:
                msus = 0

            return datetime.timedelta(
                hours=int(hours), minutes=int(minutes),
                seconds=int(seconds), microseconds=int(msus)
            )

        except Exception as exc:
            _logger.debug(f"Failed to parse timedelta string '{x}'",
                          exc_info=exc)
            return None

    elif isinstance(x, datetime.timedelta):
        return x

    else:
        return None


def to_datetime(x: Union[str, datetime.datetime]) \
        -> Optional[datetime.datetime]:
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
    """
    if isinstance(x, str) and x:
        try:
            date, time = x.strip('Z').split('T')
            year, month, day = date.split('-')
            hours, minutes, seconds = time.split(':')
            if '.' in seconds:
                seconds, msus = seconds.split('.')
                if len(msus) < 6:
                    msus = msus + '0' * (6 - len(msus))
                elif len(msus) > 6:
                    msus = msus[0:6]
            else:
                msus = 0

            return datetime.datetime(
                int(year), int(month), int(day), int(hours),
                int(minutes), int(seconds), int(msus)
            )

        except Exception as exc:
            _logger.debug(f"Failed to parse datetime string '{x}'",
                          exc_info=exc)
            return None

    elif isinstance(x, datetime.datetime):
        return x

    else:
        return None
