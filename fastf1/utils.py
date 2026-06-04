"""This is a collection of various functions."""
import warnings

import numpy as np
import pandas as pd

import fastf1


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

        plotting.setup_mpl(color_scheme='fastf1')

        session = ff1.get_session(2021, 'Emilia Romagna', 'Q')
        session.load()
        lec = session.laps.pick_drivers('LEC').pick_fastest()
        ham = session.laps.pick_drivers('HAM').pick_fastest()

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
    """Recursive dict get.

    .. deprecated:: 3.2.0
        This function was never meant to be part of the public API and
        has been moved to ``fastf1.internals._utils``. Use that instead.

    Args:
        d: dictionary
        keys: variable number of keys
        default_none: return None instead of empty dict on missing key

    Returns:
        The value at the nested key path, or None/empty dict on missing keys.
    """
    warnings.warn(
        "`fastf1.utils.recursive_dict_get` is deprecated and will be removed. "
        "Use `fastf1.internals._utils.recursive_dict_get` instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from fastf1.internals._utils import recursive_dict_get as _rdg
    return _rdg(d, *keys, default_none=default_none)


def to_timedelta(x):
    """Fast timedelta object creation from a time string.

    .. deprecated:: 3.2.0
        This function was never meant to be part of the public API and
        has been moved to ``fastf1.internals._utils``. Use that instead.

    Args:
        x: timestamp string or datetime.timedelta

    Returns:
        datetime.timedelta or None
    """
    warnings.warn(
        "`fastf1.utils.to_timedelta` is deprecated and will be removed. "
        "Use `fastf1.internals._utils.to_timedelta` instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from fastf1.internals._utils import to_timedelta as _ttd
    return _ttd(x)


def to_datetime(x):
    """Fast datetime object creation from a date string.

    .. deprecated:: 3.2.0
        This function was never meant to be part of the public API and
        has been moved to ``fastf1.internals._utils``. Use that instead.

    Args:
        x: timestamp string or datetime.datetime

    Returns:
        datetime.datetime or None
    """
    warnings.warn(
        "`fastf1.utils.to_datetime` is deprecated and will be removed. "
        "Use `fastf1.internals._utils.to_datetime` instead.",
        DeprecationWarning,
        stacklevel=2
    )
    from fastf1.internals._utils import to_datetime as _tdt
    return _tdt(x)