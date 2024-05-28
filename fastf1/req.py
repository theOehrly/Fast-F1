"""
All HTTP requests that are performed by FastF1 go through its caching and
rate limiting system.

Caching is enabled by default in FastF1 and most of the time, you do not need
to worry about caching at all. It will simply happen automatically in the
background and speed up your programs. Disabling the cache is highly
discouraged and will generally slow down your programs.

Rate limits are applied at all times. Requests that can be served from the
cache do not count towards any rate limits. Having the cache enabled can
therefore virtually increase the rate limits.

When rate limits are exceeded, FastF1 will either...

- throttle the rate of requests, if small delays are sufficient to stay within
  the limit (soft rate limit)

- raise a :class:`fastf1.RateLimitExceededError` (hard rate limit)

"""

import collections
import datetime
import functools
import math
import os
import pickle
import re
import sys
import time
from typing import (
    Optional,
    Tuple
)

import requests
from requests_cache import CacheMixin

from fastf1.logger import get_logger


_logger = get_logger(__name__)


# A NOTE TO EVERYBODY WHO READS THIS CODE
# ##############################################
# Rate limits are defined for technical reasons.
# They are not created to simply annoy you even if they may feel annoying.
#
# Some of the APIs that FastF1 accesses are provided by individuals, free
# of charge and in their spare time. Because of that, they may have very
# limited server capacity. We should accept that and be grateful that they
# even exist in the first place.
# Other APIs may be provided by larger companies. But consequently they
# also need to cope with more traffic. We should accept their API limits as
# well.
#
# IN SHORT:
# Please do not edit API limits! If you run into API limits, it is more often
# than not the case that your code can be optimized to prevent this.
# Please optimize your code!
#
# Violating the API limits may get you or even the whole FastF1 project blocked
# from accessing a specific API. This has happened before and just causes
# unnecessary hassle for many people.


class _MinIntervalLimitDelay:
    """Ensure that there is at least a minimum delay between each request.

    Sleeps for the remaining amount of time if the last request was more recent
    than allowed by the minimum interval rule.
    """
    def __init__(self, interval: float):
        self._interval: float = interval
        self._t_last: float = 0.0

    def limit(self):
        t_now = time.time()
        if (delta := (t_now - self._t_last)) < self._interval:
            time.sleep(self._interval - delta)
        self._t_last = t_now


class _CallsPerIntervalLimitRaise:
    """Ensures that there is a maximum number of requests within a fixed
    interval of time.

    If the maximum number of allowed requests within this interval is exceeded,
    a :class:`RateLimitExceeded` exception is raised.
    """
    def __init__(self, calls: int, interval: float, info: str):
        self._interval: float = interval
        self._timestamps = collections.deque(maxlen=calls)
        self._info = info

    def limit(self):
        self._timestamps.append(time.time())
        if len(self._timestamps) == self._timestamps.maxlen:
            if self._timestamps[0] > (time.time() - self._interval):
                raise RateLimitExceededError(self._info)


class _SessionWithRateLimiting(requests.Session):
    """Apply rate limiters to requests that match a URL pattern.
    """
    _RATE_LIMITS = {
        # limits on ergast.com
        re.compile(r"^https?://(\w+\.)?ergast\.com.*"): [
            _MinIntervalLimitDelay(0.25),
            # soft limit 4 calls/sec
            _CallsPerIntervalLimitRaise(200, 60*60, "ergast.com: 200 calls/h")
            # hard limit 200 calls/h
        ]
    }

    def send(self, request, **kwargs):
        # patches rate limiting into `requests.send`
        for pattern, limiters in self._RATE_LIMITS.items():
            # match url pattern
            if pattern.match(request.url):
                for lim in limiters:
                    # apply all defined limiters
                    lim.limit()

        return super().send(request, **kwargs)


class _CachedSessionWithRateLimiting(CacheMixin, _SessionWithRateLimiting):
    """Equivalent of ``requests_cache.CachedSession```but using
    :class:`_SessionWithRateLimiting` as base instead of ``requests.Session``.
    """
    pass


class _MetaCache(type):
    def __repr__(self):
        # implements __repr__ for the Cache class itself
        if self._CACHE_DIR:
            path = self._CACHE_DIR
            size = self._convert_size(self._get_size(path))
            return f"FastF1 cache ({size}) {path}"

        return "FastF1 cache - not configured"


class Cache(metaclass=_MetaCache):
    """Pickle and requests based API cache.

    Fast-F1 will per default enable caching. While this can be disabled, it
    should almost always be left enabled to speed up the runtime of your
    0scripts and to prevent exceeding the rate limit of api servers.

    The default cache directory is defined, in order of precedence, in one
    of the following ways:

    #. A call to :func:`enable_cache`
    #. The value of the environment variable ``FASTF1_CACHE``
    #. An OS dependent default cache directory

    See below for more information on default cache directories.

    The following class-level functions are used to set up, enable and
    (temporarily) disable caching.

    .. autosummary::
        fastf1.Cache.enable_cache
        fastf1.Cache.clear_cache
        fastf1.Cache.get_cache_info
        fastf1.Cache.disabled
        fastf1.Cache.set_disabled
        fastf1.Cache.set_enabled
        fastf1.Cache.offline_mode

    The parsed API data will be saved as a pickled object.
    Raw GET and POST requests are cached in a sqlite db using the
    'requests-cache' module.

    Requests that can be served from the cache do not count towards any
    API rate limits.

    The cache has two "stages":

    - Stage 1: Caching of raw GET requests. This works for all requests.
      Cache control is employed to refresh the cached data periodically.
    - Stage 2: Caching of the parsed data. This saves a lot of time when
      running your scripts,  as parsing of the data is computationally
      expensive. Stage 2 caching is only used for some api functions.

    You can explicitly configure right at the beginning of your script:

        >>> import fastf1
        >>> fastf1.Cache.enable_cache('path/to/cache')  # doctest: +SKIP
        # change cache directory to an existing empty directory on your machine
        >>> session = fastf1.get_session(2021, 5, 'Q')
        >>> # ...

    An alternative way to set the cache directory is to configure an
    environment variable `FASTF1_CACHE`. However, this value will be
    ignored if `Cache.enable_cache()` is called.

    If no explicit location is provided, Fast-F1 will use a default location
    depending on operating system.

    - Windows: `%LOCALAPPDATA%\\\\Temp\\\\fastf1`
    - macOS: `~/Library/Caches/fastf1`
    - Linux: `~/.cache/fastf1` if `~/.cache` exists otherwise `~/.fastf1`

    Cached data can be deleted at any time to reclaim disk space. However,
    this also means you will have to redownload the same data again if you
    need which will lead to reduced performance.
    """
    _CACHE_DIR = None
    # version of the api parser code (unrelated to release version number)
    _API_CORE_VERSION = 13
    _IGNORE_VERSION = False
    _FORCE_RENEW = False

    _requests_session_cached: Optional[_CachedSessionWithRateLimiting] = None
    _requests_session: requests.Session = _SessionWithRateLimiting()
    _default_cache_enabled = False  # flag to ensure that warning about disabled cache is logged once only # noqa: E501
    _tmp_disabled = False
    _ci_mode = False

    _request_counter = 0  # count uncached requests for debugging purposes

    @classmethod
    def enable_cache(
            cls, cache_dir: str, ignore_version: bool = False,
            force_renew: bool = False,
            use_requests_cache: bool = True):
        """Enables the API cache.

        Args:
            cache_dir: Path to the directory which should be used to store
                cached data. Path needs to exist.
            ignore_version: Ignore if cached data was created with a different
                version of the API parser (not recommended: this can cause
                crashes or unrecognized errors as incompatible data may be
                loaded)
            force_renew: Ignore existing cached data. Download data and update
                the cache instead.
            use_requests_cache: Do caching of the raw GET and POST requests.
        """
        # Allow users to use paths such as %LOCALAPPDATA%
        cache_dir = os.path.expandvars(cache_dir)

        # Allow users to use paths such as ~user or ~/
        cache_dir = os.path.expanduser(cache_dir)

        if not os.path.exists(cache_dir):
            raise NotADirectoryError("Cache directory does not exist! Please "
                                     "check for typos or create it first.")
        cls._CACHE_DIR = cache_dir
        cls._IGNORE_VERSION = ignore_version
        cls._FORCE_RENEW = force_renew
        if use_requests_cache:
            cls._requests_session_cached = _CachedSessionWithRateLimiting(
                cache_name=os.path.join(cache_dir, 'fastf1_http_cache'),
                backend='sqlite',
                allowable_methods=('GET', 'POST'),
                expire_after=datetime.timedelta(hours=12),
                cache_control=True,
                stale_if_error=True,
                filter_fn=cls._custom_cache_filter
            )
            if force_renew:
                cls._requests_session_cached.cache.clear()

    @classmethod
    def requests_get(cls, *args, **kwargs):
        """Wraps `requests.Session().get()` with caching if enabled.

        All GET requests that require caching should be performed through this
        wrapper. Caching will be done if the module-wide cache has been
        enabled. Else, `requests.Session().get()` will be called without any
        caching.
        """
        cls._enable_default_cache()
        if (cls._requests_session_cached is None) or cls._tmp_disabled:
            cls._request_counter += 1
            return cls._requests_session.get(*args, **kwargs)

        if cls._ci_mode:
            # try to return a cached response first
            resp = cls._requests_session_cached.get(
                *args, only_if_cached=True, **kwargs)
            # 504 indicates that no cached response was found
            if resp.status_code != 504:
                return resp

        cls._request_counter += 1
        return cls._requests_session_cached.get(*args, **kwargs)

    @classmethod
    def requests_post(cls, *args, **kwargs):
        """Wraps `requests.Session().post()` with caching if enabled.

        All POST requests that require caching should be performed through this
        wrapper. Caching will be done if the module-wide cache has been
        enabled. Else, `requests.Session().get()` will be called without any
        caching.
        """
        cls._enable_default_cache()
        if (cls._requests_session_cached is None) or cls._tmp_disabled:
            cls._request_counter += 1
            return cls._requests_session.post(*args, **kwargs)

        if cls._ci_mode:
            # try to return a cached response first
            resp = cls._requests_session_cached.post(
                *args, only_if_cached=True, **kwargs)
            # 504 indicates that no cached response was found
            if resp.status_code != 504:
                return resp

        cls._request_counter += 1
        return cls._requests_session_cached.post(*args, **kwargs)

    @classmethod
    def delete_response(cls, url):
        """Deletes a single cached response from the cache, if caching is
        enabled. If caching is not enabled, this call is ignored."""
        if cls._requests_session_cached is not None:
            cls._requests_session_cached.cache.delete(urls=[url])

    @staticmethod
    def _custom_cache_filter(response: requests.Response):
        # this function provides custom filtering to decide which responses
        # get cached

        # workaround for Ergast returning error with status code 200
        if 'Unable to select database' in response.text:
            return False

        return True

    @classmethod
    def clear_cache(cls, cache_dir=None, deep=False):
        """Clear all cached data.

        Deletes all files in the cache directory. By default, it will clear
        the default cache directory. However, if a cache directory is
        provided as an argument this will be cleared instead. Optionally,
        the requests cache can be cleared too.

        Can be called without enabling the cache first.

        Deleting specific events or sessions is not supported but can be done
        manually (stage 2 cache). The cached data is structured by year, event
        and session. The structure is more or less self-explanatory. To delete
        specific events or sessions delete the corresponding folder within the
        cache directory. Deleting specific requests from the requests cache
        (stage 1) is not possible. To delete the requests cache only, delete
        the sqlite file in the root of the cache directory.

        Args:
            cache_dir (str): Path to the directory which is used to store
                cached data.
            deep (bool): Clear the requests cache (stage 1) too.
        """
        if cache_dir is None:
            if cls._CACHE_DIR is None:
                cache_dir = cls._get_default_cache_path()
            else:
                cache_dir = cls._CACHE_DIR

        # We need to expand the directory to support ~/
        cache_dir = os.path.expandvars(cache_dir)
        cache_dir = os.path.expanduser(cache_dir)
        if not os.path.exists(cache_dir):
            raise NotADirectoryError("Cache directory does not exist!")

        for dirpath, dirnames, filenames in os.walk(cache_dir):
            for filename in filenames:
                if filename.endswith('.ff1pkl'):
                    os.remove(os.path.join(dirpath, filename))

        if deep:
            cache_db_path = os.path.join(cache_dir, 'fastf1_http_cache.sqlite')
            if os.path.exists(cache_db_path):
                os.remove(cache_db_path)

    @classmethod
    def api_request_wrapper(cls, func):
        """Wrapper function for adding stage 2 caching to api functions.

        Args:
            func: function to be wrapped

        Returns:
            The wrapped function
        """

        @functools.wraps(func)
        def _cached_api_request(api_path, **func_kwargs):
            if cls._CACHE_DIR and not cls._tmp_disabled:
                # caching is enabled
                func_name = str(func.__name__)
                cache_file_path = cls._get_cache_file_path(api_path, func_name)

                if os.path.isfile(cache_file_path):
                    if cls._ci_mode:
                        # skip pickle cache in ci mode so that API parser code
                        # is always executed. Only http cache is active
                        return func(api_path, **func_kwargs)

                    # file exists already, try to load it
                    try:
                        cached = pickle.load(open(cache_file_path, 'rb'))
                    except:  # noqa: E722 (bare except)
                        # don't like the bare exception clause but who knows
                        # which dependency will raise which internal exception
                        # after it was updated
                        cached = None

                    if (cached is not None) and cls._data_ok_for_use(cached):
                        # cached data is ok for use, return it
                        _logger.info(f"Using cached data for {func_name}")
                        return cached['data']

                    else:
                        # cached data needs to be downloaded again and updated
                        _logger.info(f"Updating cache for {func_name}...")
                        data = func(api_path, **func_kwargs)

                        if data is not None:
                            cls._write_cache(data, cache_file_path)
                            _logger.info("Cache updated!")
                            return data

                        _logger.critical(
                            "A cache update is required but the data failed "
                            "to download. Cannot continue!\nYou may force to "
                            "ignore a cache version mismatch by using the "
                            "`ignore_version=True` keyword when enabling the "
                            "cache (not recommended)."
                        )
                        exit()

                else:  # cached data does not yet exist for this api request
                    _logger.info(f"No cached data found for {func_name}. "
                                 f"Loading data...")
                    data = func(api_path, **func_kwargs)
                    if data is not None:
                        cls._write_cache(data, cache_file_path)
                        _logger.info("Data has been written to cache!")
                        return data

                    _logger.critical("Failed to load data!")
                    exit()

            else:  # cache was not enabled
                if not cls._tmp_disabled:
                    cls._enable_default_cache()
                return func(api_path, **func_kwargs)

        return _cached_api_request

    @classmethod
    def _get_cache_file_path(cls, api_path, name):
        # extend the cache dir path using the api path and a file name
        # leading '/static/' is dropped form api path
        cache_dir_path = os.path.join(cls._CACHE_DIR, api_path[8:])
        if not os.path.exists(cache_dir_path):
            # create subfolders if they don't yet exist
            os.makedirs(cache_dir_path)

        file_name = name + '.ff1pkl'
        cache_file_path = os.path.join(cache_dir_path, file_name)
        return cache_file_path

    @classmethod
    def _data_ok_for_use(cls, cached):
        # check if cached data is ok or needs to be downloaded again
        if cls._FORCE_RENEW:
            return False
        elif cls._IGNORE_VERSION:
            return True
        elif cached['version'] == cls._API_CORE_VERSION:
            return True
        return False

    @classmethod
    def _write_cache(cls, data, cache_file_path, **kwargs):
        new_cached = dict(
            **{'version': cls._API_CORE_VERSION, 'data': data},
            **kwargs
        )
        with open(cache_file_path, 'wb') as cache_file_obj:
            pickle.dump(new_cached, cache_file_obj)

    @classmethod
    def _get_default_cache_path(cls):
        if sys.platform == "linux":
            # If .cache exists we will use it. Otherwise, ~/
            tmp = os.path.expanduser("~/.cache")
            if os.path.exists(tmp):
                return r"~/.cache/fastf1"
            else:
                return r"~/.fastf1"
        elif sys.platform == "darwin":
            return r"~/Library/Caches/fastf1"
        elif sys.platform == "win32":
            return r"%LOCALAPPDATA%\Temp\fastf1"
        else:
            return None

    @classmethod
    def _enable_default_cache(cls):
        if not cls._CACHE_DIR and not cls._default_cache_enabled:
            cache_dir = None
            if "FASTF1_CACHE" in os.environ:
                cache_dir = os.environ.get("FASTF1_CACHE")
            else:
                cache_dir = cls._get_default_cache_path()

            if cache_dir is not None:
                # Ensure the default cache folder exists
                cache_dir = os.path.expandvars(cache_dir)
                cache_dir = os.path.expanduser(cache_dir)
                if not os.path.exists(cache_dir):
                    try:
                        os.mkdir(cache_dir, mode=0o0700)
                    except Exception as err:
                        _logger.error("Failed to create cache directory {0}. "
                                      "Error {1}".format(cache_dir, err))
                        raise

                # Enable cache with default
                cls.enable_cache(cache_dir)
                _logger.warning(
                    f"DEFAULT CACHE ENABLED! "
                    f"({cls._convert_size(cls._get_size(cache_dir))}) "
                    f"{cache_dir}"
                )
            else:
                # warn only once and only if cache is not enabled
                _logger.warning(
                    "\n\nNO CACHE! Api caching has not been enabled! \n\t"
                    "It is highly recommended to enable this feature for much "
                    "faster data loading!\n\t"
                    "Use `fastf1.Cache.enable_cache('path/to/cache/')`\n")

                cls._default_cache_enabled = True

    @classmethod
    def disabled(cls):
        """Returns a context manager object that creates a context within
        which the cache is temporarily disabled.

        Example::

            with Cache.disabled():
                # no caching takes place here
                ...

        .. note::
            The context manager is not multithreading-safe
        """
        return _NoCacheContext()

    @classmethod
    def set_disabled(cls):
        """Disable the cache while keeping the configuration intact.

        This disables stage 1 and stage 2 caching!

        You can enable the cache at any time using :func:`set_enabled`

        .. note:: You may prefer to use :func:`disabled` to get a context
            manager object and disable the cache only within a specific
            context.

        .. note::
            This function is not multithreading-safe
        """
        cls._tmp_disabled = True

    @classmethod
    def set_enabled(cls):
        """Enable the cache after it has been disabled with
        :func:`set_disabled`.

        .. warning::
            To enable the cache it needs to be configured properly. You need
            to call :func`enable_cache` once to enable the cache initially.
            :func:`set_enabled` and :func:`set_disabled` only serve to
            (temporarily) disable the cache for specific parts of code that
            should be run without caching.

        .. note::
            This function is not multithreading-safe
        """
        cls._tmp_disabled = False

    @classmethod
    def offline_mode(cls, enabled: bool):
        """Enable or disable offline mode.

        In this mode, no actual requests will be sent and only cached data is
        returned. This can be useful for freezing the state of the cache or
        working with an unstable internet connection.

        Args:
            enabled: sets the state of offline mode to 'enabled' (``True``)
                or 'disabled' (``False``)
        """
        if cls._requests_session_cached is None:
            cls._enable_default_cache()
        cls._requests_session_cached.settings.only_if_cached = enabled

    @classmethod
    def ci_mode(cls, enabled: bool):
        """Enable or disable CI mode.

        In this mode, cached requests will be reused even if they are expired.
        Only uncached data will actually be requested and is then cached. This
        means, as long as CI mode is enabled, every request is only ever made
        once and reused indefinitely.

        This serves two purposes. First, reduce the number of requests that is
        sent on when a large number of tests is run in parallel, potentially
        in multiple environments simultaneously. Second, make test runs more
        predictable because data usually does not change between runs.

        Additionally, the pickle cache (stage 2) is disabled completely, so
        no parsed data is cached. This means that the API parser code is
        always executed and not skipped due to caching.
        """
        cls._ci_mode = enabled

    @classmethod
    def get_cache_info(cls) -> Tuple[Optional[str], Optional[int]]:
        """Returns information about the cache directory and its size.

        If the cache is not configured, None will be returned for both the
        cache path and the cache size.

        Returns:
            A tuple of ``(path, size)`` if the cache is configured, else
            ``(None, None)``. The cache size is given in bytes.
        """
        path = cls._CACHE_DIR
        if path is not None:
            size = cls._get_size(path)
        else:
            size = None

        return path, size

    @classmethod
    def _convert_size(cls, size_bytes):  # https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python # noqa: E501
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return "%s %s" % (s, size_name[i])

    @classmethod
    def _get_size(cls, start_path='.'):  # https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python # noqa: E501
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)

        return total_size


class _NoCacheContext:
    def __enter__(self):
        Cache.set_disabled()

    def __exit__(self, exc_type, exc_val, exc_tb):
        Cache.set_enabled()


# TODO: document
class RateLimitExceededError(Exception):
    """Raised if a hard rate limit is exceeded."""
    pass
