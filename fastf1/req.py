import collections
import datetime
import functools
import math
import os
import pickle
import re
import sys
import time
import warnings
from typing import (
    Any,
    Literal
)

import requests
from requests_cache import CacheMixin

from fastf1.exceptions import RateLimitExceededError
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
            t_now += self._interval - delta
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
        if (len(self._timestamps) == self._timestamps.maxlen and
            self._timestamps[0] > (time.time() - self._interval)):
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
        ],
        # general limits on all other APIs
        re.compile(r"^https?://.+\..+"): [
            _MinIntervalLimitDelay(0.25),
            # soft limit 4 calls/sec
            _CallsPerIntervalLimitRaise(500, 60 * 60, "any API: 500 calls/h")
            # hard limit 200 calls/h
        ],
    }

    def send(self, request, **kwargs):
        # patches rate limiting into `requests.send`
        for pattern, limiters in self._RATE_LIMITS.items():
            # match url pattern
            if request.url is None:
                continue
            if pattern.match(request.url):
                for lim in limiters:
                    # apply all defined limiters
                    lim.limit()

        return super().send(request, **kwargs)


class _CachedSessionWithRateLimiting(CacheMixin, _SessionWithRateLimiting):
    """Equivalent of ``requests_cache.CachedSession```but using
    :class:`_SessionWithRateLimiting` as base instead of ``requests.Session``.
    """


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
    scripts and to prevent exceeding the rate limit of api servers.

    The default cache directory is defined, in order of precedence, in one
    of the following ways:

    #. A call to :func:`configure`
    #. The value of the environment variable ``FASTF1_CACHE``
    #. An OS dependent default cache directory

    See below for more information on default cache directories.

    The following class-level functions are used to set up, enable and
    (temporarily) disable caching.

    .. autosummary::
        enable_cache
        configure
        clear_cache
        get_cache_info
        disabled
        set_disabled
        set_enabled
        offline_mode

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
        >>> fastf1.Cache.configure(cache_dir='path/to/cache')  # doctest: +SKIP
        # change cache directory to an existing empty directory on your machine
        >>> session = fastf1.get_session(2021, 5, 'Q')
        >>> # ...

    When doing this, :func:`configure` must be called right after your
    imports and before any other FastF1 related functionality is called to
    ensure that the cache is configured correctly.

    An alternative way to set the cache directory is to configure an
    environment variable `FASTF1_CACHE`. However, this value will be
    ignored if a different cache directory is configured via
    `Cache.configure()`.

    If no explicit location is provided, Fast-F1 will use a default location
    depending on the operating system.

    - Windows: `%LOCALAPPDATA%\\\\Temp\\\\fastf1`
    - macOS: `~/Library/Caches/fastf1`
    - Linux: `~/.cache/fastf1` if `~/.cache` exists otherwise `~/.fastf1`

    Cached data can be deleted at any time to reclaim disk space. However,
    this also means you will have to redownload the same data again if you
    need, which will lead to reduced performance.
    """
    _CACHE_DIR = None
    # version of the api parser code (unrelated to release version number)
    _API_CORE_VERSION = 15
    _IGNORE_VERSION = False
    _FORCE_RENEW = False

    _requests_session_cached: _CachedSessionWithRateLimiting | None = None
    _requests_session: requests.Session = _SessionWithRateLimiting()
    _no_cached_warned = False  # flag to ensure that warning about disabled cache is logged once only # noqa: E501
    _tmp_disabled = False
    _ci_mode = False

    @classmethod
    def enable_cache(
            cls,
            cache_dir: str,
            ignore_version: bool = False,
            force_renew: bool = False,
            use_requests_cache: bool = True):
        """Enables the API cache.

        .. deprecated:: 3.9.0

            :func:`enable_cache` will be removed in a future version.
            Use :func:`configure` instead.`

        """
        warnings.warn("`.enable_cache` is deprecated and will be removed in a"
                      "future version. Use `.configure` instead.",
                      FutureWarning)

        cls.configure(
            cache_dir=cache_dir,
            ignore_version=ignore_version,
            force_renew=force_renew,
            use_requests_cache=use_requests_cache
        )

    @classmethod
    def configure(
        cls, *,
        cache_dir: str | None = None,
        force_renew: bool = False,
        ignore_version: bool = False,
        use_requests_cache: bool = True
    ):
        sanitized_cached_dir = cls._ensure_cache_directory(cache_dir)
        if sanitized_cached_dir is None:
            return

        cls._CACHE_DIR = cache_dir
        cls._IGNORE_VERSION = ignore_version
        cls._FORCE_RENEW = force_renew

        if use_requests_cache:
            req_cache_file = os.path.join(
                sanitized_cached_dir, 'fastf1_http_cache'
            )
            cls._requests_session_cached = _CachedSessionWithRateLimiting(
                cache_name=req_cache_file,
                backend='sqlite',
                allowable_methods=('GET', 'POST'),
                expire_after=datetime.timedelta(hours=12),
                cache_control=True,
                stale_if_error=True
            )
            if force_renew:
                cls._requests_session_cached.cache.clear()

    @classmethod
    def requests_get(cls, url: str, **kwargs):
        """Wraps `requests.Session().get()` with caching if enabled.

        All GET requests that require caching should be performed through this
        wrapper. Caching will be done if the module-wide cache has been
        enabled. Else, `requests.Session().get()` will be called without any
        caching.
        """
        cls._ensure_caching()
        if (cls._requests_session_cached is None) or cls._tmp_disabled:
            return cls._requests_session.get(url, **kwargs)

        if cls._ci_mode:
            # try to return a cached response first
            mod_kwargs = {**kwargs, 'only_if_cached': True}
            resp = cls._cached_request('GET', url, **mod_kwargs)
            # 504 indicates that no cached response was found
            if resp.status_code != 504:
                return resp

        return cls._cached_request('GET', url, **kwargs)

    @classmethod
    def requests_post(cls, url: str, **kwargs):
        """Wraps `requests.Session().post()` with caching if enabled.

        All POST requests that require caching should be performed through this
        wrapper. Caching will be done if the module-wide cache has been
        enabled. Else, `requests.Session().get()` will be called without any
        caching.
        """
        cls._ensure_caching()
        if (cls._requests_session_cached is None) or cls._tmp_disabled:
            return cls._requests_session.post(url, **kwargs)

        if cls._ci_mode:
            # try to return a cached response first
            mod_kwargs = {**kwargs, 'only_if_cached': True}
            resp = cls._cached_request('POST', url, **mod_kwargs)
            # 504 indicates that no cached response was found
            if resp.status_code != 504:
                return resp

        return cls._cached_request('POST', url, **kwargs)

    @classmethod
    def _cached_request(cls,
                        method: Literal['GET', 'POST'],
                        url: str,
                        **kwargs):
        if cls._requests_session_cached is None:
            raise RuntimeError("A cached request was attempted but the cache "
                               "is not enabled.")

        # catch TypeError raised by outdated requests-cache version if the
        # cache was created with a newer version
        # github.com/requests-cache/requests-cache/issues/973
        if method == 'GET':
            func = cls._requests_session_cached.get
        elif method == 'POST':
            func = cls._requests_session_cached.post
        else:
            raise ValueError("Invalid method. Must be 'GET' or 'POST'.")

        try:
            response = func(url, **kwargs)
        except TypeError:
            warnings.warn("You are using an outdated version of "
                          "requests-cache. Consider upgrading.", UserWarning)
            cls._requests_session_cached.cache.delete(urls=[url])
            response = func(url, **kwargs)
        return response

    @classmethod
    def delete_response(cls, url: str):
        """Deletes a single cached response from the cache, if caching is
        enabled. If caching is not enabled, this call is ignored."""
        if cls._requests_session_cached is not None:
            cls._requests_session_cached.cache.delete(urls=[url])

    @classmethod
    def clear_cache(
            cls,
            cache_dir: str | None = None,
            deep: bool = False
    ):
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
        if cache_dir is None and cls._CACHE_DIR is not None:
            sanitized_cache_dir = cls._CACHE_DIR
        else:
            sanitized_cache_dir = cls._ensure_cache_directory(cache_dir)

        if sanitized_cache_dir is None:
            raise ValueError("Unable to clear cache. Could not determine "
                             "cache directory.")

        for dirpath, _dirnames, filenames in os.walk(sanitized_cache_dir):
            for filename in filenames:
                if filename.endswith('.ff1pkl'):
                    os.remove(os.path.join(dirpath, filename))

        if deep:
            cache_db_path = os.path.join(sanitized_cache_dir,
                                         'fastf1_http_cache.sqlite')
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
                        with open(cache_file_path, 'rb') as cache_file:
                            cached = pickle.load(cache_file)
                    except:  # noqa: E722 (bare except)
                        # don't like the bare exception clause but who knows
                        # which dependency will raise which internal exception
                        # after it was updated
                        cached = None

                    if not isinstance(cached, dict):
                        cached = None

                    if (cached is not None) and cls._data_ok_for_use(cached):
                        # cached data is ok for use, return it
                        _logger.info(f"Using cached data for {func_name}")
                        return cached['data']

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
                return func(api_path, **func_kwargs)

        return _cached_api_request

    @classmethod
    def _get_cache_file_path(cls, api_path: str, name: str):
        # extend the cache dir path using the api path and a file name
        # leading '/static/' is dropped from api path
        cache_dir_path = os.path.join(cls._CACHE_DIR, api_path[8:])
        if not os.path.exists(cache_dir_path):
            # create subfolders if they don't yet exist
            os.makedirs(cache_dir_path)

        file_name = name + '.ff1pkl'
        return os.path.join(cache_dir_path, file_name)

    @classmethod
    def _data_ok_for_use(cls, cached: dict):
        # check if cached data is ok or needs to be downloaded again
        if cls._FORCE_RENEW:
            return False
        return (
            cls._IGNORE_VERSION or
            cached['version'] == cls._API_CORE_VERSION
        )

    @classmethod
    def _write_cache(
            cls,
            data: Any,
            cache_file_path: str,
            **kwargs
    ):
        new_cached = dict(
            version=cls._API_CORE_VERSION, data=data,
            **kwargs
        )
        with open(cache_file_path, 'wb') as cache_file_obj:
            pickle.dump(new_cached, cache_file_obj)

    @classmethod
    def _get_default_cache_path(cls) -> str | None:
        if sys.platform == "linux":
            # If .cache exists we will use it. Otherwise, ~/
            tmp = os.path.expanduser("~/.cache")
            if os.path.exists(tmp):
                cache_dir = r"~/.cache/fastf1"
            cache_dir = r"~/.fastf1"
        elif sys.platform == "darwin":
            cache_dir = r"~/Library/Caches/fastf1"
        elif sys.platform == "win32":
            cache_dir = r"%LOCALAPPDATA%\Temp\fastf1"
        else:
            # unknown platform, unable to get cache directory
            return None

        cache_dir = os.path.expandvars(cache_dir)
        cache_dir = os.path.expanduser(cache_dir)
        if not os.path.exists(cache_dir):
            try:
                os.mkdir(cache_dir, mode=0o0700)
            except Exception as err:
                _logger.error(
                    f"Failed to create cache directory "
                    f"{cache_dir}. Error {err}"
                )
                raise

        return cache_dir

    @classmethod
    def _ensure_cache_directory(
            cls,
            user_cache_dir: str| None = None
    ) -> str | None:
        if user_cache_dir is not None:
            # Allow users to use paths such as %LOCALAPPDATA%
            cache_dir = str(os.path.expandvars(user_cache_dir))
        elif "FASTF1_CACHE" in os.environ:
            cache_dir = os.environ.get("FASTF1_CACHE")
        else:
            cache_dir = cls._get_default_cache_path()

        if cache_dir is None:
            warnings.warn(
                f"Failed to get a default cache path "
                f"(platform={sys.platform}). "
                f"Please configure the cache directory manually."
            )
            return None

        # Allow users to use paths such as ~user or ~/
        cache_dir = os.path.expanduser(cache_dir)

        if not os.path.exists(cache_dir):
            raise NotADirectoryError("Cache directory does not exist! Please "
                                     "check for typos or create it first.")

        return cache_dir

    @classmethod
    def _ensure_caching(cls):
        if not cls._CACHE_DIR and not cls._no_cached_warned:
            cls.configure()  # enable using defaults

            if not cls._CACHE_DIR:
                # warn only once and only if cache is not enabled
                _logger.warning(
                    "\n\nNO CACHE! Api caching has not been enabled! \n\t"
                    "It is highly recommended to enable this feature for much "
                    "faster data loading!\n\t"
                    "Use `fastf1.Cache.configure(...)`\n")

                cls._no_cached_warned = True
                return

            _logger.warning(
                f"DEFAULT CACHE ENABLED! "
                f"({cls._convert_size(cls._get_size(cls._CACHE_DIR))}) "
                f"{cls._CACHE_DIR}"
            )

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
            to call :func`configure` once to enable the cache initially.
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

        .. note::

            This function must be called after :func:`configure` when
            using a custom cache directory.

        Args:
            enabled: sets the state of offline mode to 'enabled' (``True``)
                or 'disabled' (``False``)
        """
        if cls._requests_session_cached is None:
            cls._ensure_caching()
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

        .. deprecated:: v3.9.0

            This function is deprecated and will be removed in a future
            release.

        .. note::

            This function must be called after :func:`configure` when
            using a custom cache directory.
        """
        warnings.warn("CI mode is deprecated and will be removed in a "
                      "future release.", FutureWarning)
        cls._ci_mode = enabled

    @classmethod
    def get_cache_info(cls) -> tuple[str | None, int | None]:
        """Returns information about the cache directory and its size.

        If the cache is not configured, None will be returned for both the
        cache path and the cache size.

        Returns:
            A tuple of ``(path, size)`` if the cache is configured, else
            ``(None, None)``. The cache size is given in bytes.
        """
        path = cls._CACHE_DIR
        size = cls._get_size(path) if path else None

        return path, size

    @classmethod
    def _convert_size(cls, size_bytes: int):  # https://stackoverflow.com/questions/5194057/better-way-to-convert-file-sizes-in-python # noqa: E501
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    @classmethod
    def _get_size(cls, start_path: str = '.'):  # https://stackoverflow.com/questions/1392413/calculating-a-directorys-size-using-python # noqa: E501
        total_size = 0
        for dirpath, _dirnames, filenames in os.walk(start_path):
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
