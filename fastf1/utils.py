"""
:mod:`fastf1.utils` - Utils module
==================================
"""
import os
import functools
import requests_cache
import pandas as pd
import numpy as np
import logging
from fastf1 import core

CACHE_ENABLE = False
CACHE_PATH = ""


def enable_cache(path):
    """Enable cache for parsed data.

    If not enabled, raw http requests are still cached, data is quite
    fixed and shouldn't really change.

    :param path: Path to a folder which to use as cache directory
    :type path: str
    """
    global CACHE_ENABLE, CACHE_PATH
    CACHE_PATH = path

    os.makedirs(CACHE_PATH, exist_ok=True)
    requests_cache.install_cache(os.path.join(path, 'fastf1_http_cache'), allowable_methods=('GET', 'POST'))

    CACHE_ENABLE = True


def clear_cache(deep=False):
    """Removes from disk cached data. Just in case you feel the need of
    a fresh start or you have too much bytes laying around.
    Use it with parsimony. In case of a major update you may want to call
    this function. It may solve conflicts rising on unexpected data
    structures.
    The cache needs to be enabled first, so that the cache path is known.

    Args:
        deep (=False, optional): If true, going for removal of http
                                 cache as well.
    """
    file_names = os.listdir(CACHE_PATH)
    for file_name in file_names:
        if file_name.endswith('.pkl'):
            os.remove(os.path.join(CACHE_PATH, file_name))    
    if deep:
        requests_cache.clear()


def laps_file_name(api_path):
    # api path used as session identifier
    return f"{'_'.join(api_path.split('/')[-3:-1])}_laps.pkl"


def delta_time(reference_lap, compare_lap):
    # TODO what is this and why is it here?
    """Calculates the delta time of a given lap, along the 'Space' axis
    of the reference lap.

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
        ax.plot(lec.telemetry['Space'], lec.telemetry['Speed'],
                color=plotting.TEAM_COLORS[lec['Team']])
        ax.plot(ham.telemetry['Space'], ham.telemetry['Speed'],
                color=plotting.TEAM_COLORS[ham['Team']])
        twin = ax.twinx()
        twin.plot(ham.telemetry['Space'], utils.delta_time(ham, lec),
                  '--', color=plotting.TEAM_COLORS[lec['Team']])
        plt.show()

    .. image:: _static/delta_time.svg
        :target: _static/delta_time.svg

    Args:
        reference_lap (pd.Series): The lap taken as reference
        compare_lap (pd.Series): The lap to compare

    Returns:
        A pd.Series of type `float64` with the delta in seconds.

    """
    ref, lap = reference_lap.telemetry, compare_lap.telemetry

    def mini_pro(stream):
        # Ensure that all samples are interpolated
        dstream_start = stream[1] - stream[0]
        dstream_end = stream[-1] - stream[-2]
        return np.concatenate([[stream[0] - dstream_start], stream, [stream[-1] + dstream_end]])

    ltime = mini_pro(lap['Time'].dt.total_seconds().to_numpy())
    lspace = mini_pro(lap['Space'].to_numpy())
    lap_time = np.interp(ref['Space'], lspace, ltime)

    return lap_time - ref['Time'].dt.total_seconds()


def _cached_laps(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        if not CACHE_ENABLE:
            return func(*args, **kwargs)
        session = args[0]
        pkl = os.path.join(CACHE_PATH, _laps_file_name(session.api_path))
        if os.path.isfile(pkl):
            session.laps = core.Laps(pd.read_pickle(pkl))
        else:
            laps = func(*args, **kwargs)
            os.makedirs(CACHE_PATH, exist_ok=True)
            laps.to_pickle(pkl)
        return session.laps
    return decorator


def _laps_file_name(api_path):
    # api path used as session identifier
    return f"{'_'.join(api_path.split('/')[-3:-1])}_laps.pkl"
