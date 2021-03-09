"""
:mod:`fastf1.utils` - Utils module
==================================
"""
from functools import reduce

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def delta_time(reference_lap, compare_lap):
    # TODO move somewhere else
    """Calculates the delta time of a given lap, along the 'Distance' axis
    of the reference lap.

    .. warning:: This is a nice gimmick but not actually very accurate which
        is an inherent problem from the way this is calculated currently (There
        may not be a better way though). In comparison with the sector times and the
        differences that can be calculated from these, there are notable differences!
        You should always verify the result against sector time differences or find a
        different way for verification.

    Here is an example that compares the quickest laps of Leclerc and
    Hamilton from Barcelona 2019 Qualifying::

        import fastf1 as ff1
        from fastf1 import plotting
        from fastf1 import utils
        from matplotlib import pyplot as plt

        quali = ff1.get_session(2019, 'Spain', 'Q')
        laps = quali.load_laps()
        lec = laps.pick_driver('LEC').pick_fastest()
        ham = laps.pick_driver('HAM').pick_fastest()

        fig, ax = plt.subplots()
        ax.plot(lec.telemetry['Distance'], lec.telemetry['Speed'],
                color=plotting.TEAM_COLORS[lec['Team']])
        ax.plot(ham.telemetry['Distance'], ham.telemetry['Speed'],
                color=plotting.TEAM_COLORS[ham['Team']])
        delta_time, dt_ref = utils.delta_time(ham, lec)
        twin = ax.twinx()
        twin.plot(dt_ref['Distance'], delta_time, '--', color=plotting.TEAM_COLORS[lec['Team']])
        plt.show()

    .. image:: _static/delta_time.svg
        :target: _static/delta_time.svg

    Args:
        reference_lap (pd.Series): The lap taken as reference
        compare_lap (pd.Series): The lap to compare

    Returns:
        tuple: (delta, reference, comparison)
          - pd.Series of type `float64` with the delta in seconds.
          - :class:`Telemetry` for the reference lap
          - :class:`Telemetry` for the comparison lap
            Use the return telemetry for plotting to make sure you have
            telemetry data that was created with the same settings!
    """
    ref = reference_lap.get_car_data(interpolate_edges=True).add_distance()
    comp = compare_lap.get_car_data(interpolate_edges=True).add_distance()

    def mini_pro(stream):
        # Ensure that all samples are interpolated
        dstream_start = stream[1] - stream[0]
        dstream_end = stream[-1] - stream[-2]
        return np.concatenate([[stream[0] - dstream_start], stream, [stream[-1] + dstream_end]])

    ltime = mini_pro(comp['Time'].dt.total_seconds().to_numpy())
    ldistance = mini_pro(comp['Distance'].to_numpy())
    lap_time = np.interp(ref['Distance'], ldistance, ltime)

    delta = lap_time - ref['Time'].dt.total_seconds()

    return delta, ref, comp


def recursive_dict_get(d, *keys):
    """Recursive dict get. Can take an arbitrary number of keys and returns an empty
    dict if any key does not exist.
    https://stackoverflow.com/a/28225747"""
    return reduce(lambda c, k: c.get(k, {}), keys, d)


def to_timedelta(x):
    """Fast timedelta object creation from a time string

    | String format: hh:mm:ss.ms
    | Hours or minutes do not necessarily need to be present.
    | Hours minutes and seconds always need to be zero padded so as to have two digits.
    | An arbitrary part of the left side can be skipped for example 'mm:ss.ms' is acceptable too

    Args:
        x (str): [hh:][mm:]ss.ms
    Returns:
        timedelta object
    """
    # TODO should "fix" this; it does work for the given use case but actually does not quite behave as expected
    # this is faster than using pd.timedelta on a string
    if isinstance(x, str):
        def tdformat(s):
            h, m, sms = s.split(':')
            s, ms = sms.split('.')
            return {'hours': int(h), 'minutes': int(m), 'seconds': int(s), 'milliseconds': int(ms)}

        if len(x) and isinstance(x, str):
            return timedelta(**tdformat('00:00:00.000'[:-len(x)] + x))
    elif isinstance(x, timedelta):
        return x
    return pd.to_timedelta(x)  # attempted catch-all; slow!


def to_datetime(x):
    """Fast datetime object creation from a date string.

    Permissible formats:
        For example '2020-12-13T13:27:320000Z' with:
            - seconds or no seconds
            - optional milliseconds and microseconds with
              arbitrary precision
            - with optional trailing letter 'Z'
    """
    date, time = x.strip('Z').split('T')
    year, month, day = date.split('-')
    hours, minutes, seconds = time.split(':')
    if '.' in seconds:
        seconds, msus = seconds.split('.')
        if len(msus) < 6:
            msus = msus+'0'*(6-len(msus))
        elif len(msus) > 6:
            msus = msus[0:6]
    else:
        msus = 0

    return datetime(int(year), int(month), int(day), int(hours),
                    int(minutes), int(seconds), int(msus))
