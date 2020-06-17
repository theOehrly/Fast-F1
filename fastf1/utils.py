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
    requests_cache.install_cache(os.path.join(path, 'fastf1_http_cache'), allowable_methods=('GET', 'POST'))

    CACHE_PATH = path
    CACHE_ENABLE = True


def clear_cache(deep=False):
    """Removes from disk cached data. Just in case you feel the need of
    a fresh start or you have too much bytes laying around.
    Use it with parsimony. In case of major update you may want to call
    this function, which will solve conflicts rising on unexpected data
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
