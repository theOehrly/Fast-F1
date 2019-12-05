"""
:mod:`fastf1.utils` - Utils module
==================================
"""
import os
import functools
import pandas as pd
from fastf1 import core

CACHE_PATH = os.environ['HOME'] + '/Documents/FF1Data'

CACHE_ENABLE = True
"""Boolean: Enable/Disable cache for parsed data (Everything under
./F1_Data). Note that raw requests are still cached, data is quite fixed
and shouldn't really change..
"""

_CACHED_PANDA_ENABLE = False

def _cached_panda(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        if not _CACHED_PANDA_ENABLE:
            return func(*args, **kwargs)
        path = args[0]
        name = func.__name__
        pkl = f"{CACHE_PATH}/{'_'.join(path.split('/')[-3:-1])}_{name}.pkl"
        if os.path.isfile(pkl):
            print(f"Hit cache for {pkl}")
            df = pd.read_pickle(pkl)
        else:
            df = func(*args, **kwargs)
            os.makedirs(CACHE_PATH, exist_ok=True)
            df.to_pickle(pkl)
        return df
    return decorator


def _cached_laps(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        if not CACHE_ENABLE:
            return func(*args, **kwargs)
        session = args[0]
        pkl = os.path.join(CACHE_PATH, laps_file_name(session.api_path))
        if os.path.isfile(pkl):
            session.laps = core.Laps(pd.read_pickle(pkl))
        else:
            laps = func(*args, **kwargs)
            os.makedirs(CACHE_PATH, exist_ok=True)
            laps.to_pickle(pkl)
        return session.laps
    return decorator


def laps_file_name(api_path):
    # api path used as session identifier
    return f"{'_'.join(api_path.split('/')[-3:-1])}_laps.pkl"
