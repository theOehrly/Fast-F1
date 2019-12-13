"""
:mod:`fastf1.utils` - Utils module
==================================
"""
import os
import functools
import requests_cache
import pandas as pd
import logging
from fastf1 import core

CACHE_PATH = os.environ['HOME'] + '/Documents/FF1Data'

CACHE_ENABLE = True
"""Boolean: Enable/Disable cache for parsed data (Everything under
./F1_Data). Note that raw http requests are still cached, data is quite
fixed and shouldn't really change..
"""

requests_cache.install_cache(os.path.join(CACHE_PATH, 'fastf1_http_cache'),
                             allowable_methods=('GET', 'POST'))

def clear_cache(deep=False):
    """Removes from disk cached data. Just in case you feel the need of
    a fresh start or you have too much bytes laying around.
    Use it with parsimony. In case of major update you may want to call
    this function, which will solve conflicts rising on unexpected data
    structures.

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
