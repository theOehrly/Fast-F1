"""
Api Functions - :mod:`fastf1.api`
=================================

.. note:: The functions listed here are primarily for internal use within
    FastF1. While you can use these functions directly, it is usually
    better to use the functionality provided by the data objects
    in :mod:`fastf1.core` instead.

A collection of functions to interface with the F1 web api.

.. autosummary::
   :nosignatures:

   timing_data
   timing_app_data
   car_data
   position_data
   track_status_data
   session_status_data
   race_control_messages
   driver_info
   weather_data
   fetch_page
   parse

"""
import base64
import datetime
import functools
import json
import logging
import os
import pickle
import zlib

import numpy as np
import pandas as pd
import requests
import requests_cache

from fastf1.utils import recursive_dict_get, to_timedelta, to_datetime


base_url = 'https://livetiming.formula1.com'

headers = {
  'Host': 'livetiming.formula1.com',
  'Connection': 'close',
  'TE': 'identity',
  'User-Agent': 'BestHTTP',
  'Accept-Encoding': 'gzip, identity',
}

pages = {
  'session_data': 'SessionData.json',  # track + session status + lap count
  'session_info': 'SessionInfo.json',  # more rnd
  'archive_status': 'ArchiveStatus.json',  # rnd=1880327548
  'heartbeat': 'Heartbeat.jsonStream',  # Probably time synchronization?
  'audio_streams': 'AudioStreams.jsonStream',  # Link to audio commentary
  'driver_list': 'DriverList.jsonStream',  # Driver info and line story
  'extrapolated_clock': 'ExtrapolatedClock.jsonStream',  # Boolean
  'race_control_messages': 'RaceControlMessages.json',  # Flags etc
  'session_status': 'SessionStatus.jsonStream',  # Start and finish times
  'team_radio': 'TeamRadio.jsonStream',  # Links to team radios
  'timing_app_data': 'TimingAppData.jsonStream',  # Tyres and laps (juicy)
  'timing_stats': 'TimingStats.jsonStream',  # 'Best times/speed' useless
  'track_status': 'TrackStatus.jsonStream',  # SC, VSC and Yellow
  'weather_data': 'WeatherData.jsonStream',  # Temp, wind and rain
  'position': 'Position.z.jsonStream',  # Coordinates, not GPS? (.z)
  'car_data': 'CarData.z.jsonStream',  # Telemetry channels (.z)
  'content_streams': 'ContentStreams.jsonStream',  # Lap by lap feeds
  'timing_data': 'TimingData.jsonStream',  # Gap to car ahead
  'lap_count': 'LapCount.jsonStream',  # Lap counter
  'championship_prediction': 'ChampionshipPrediction.jsonStream'  # Points
}
"""Known API requests"""


class Cache:
    """Pickle and requests based API cache.

    The parsed API data will be saved as a pickled object.
    Raw GET requests are cached in a sqlite db using the 'requests-cache'
    module.

    Caching should almost always be enabled to speed up the runtime of your
    scripts and to prevent exceeding the rate limit of api servers.
    FastF1 will print an annoyingly obnoxious warning message if you do not
    enable caching.

    The cache has two "stages".

        - Stage 1: Caching of raw GET requests. This works for all requests.
          Cache control is employed to refresh the cached data periodically.
        - Stage 2: Caching of the parsed data. This saves a lot of time when
          running your scripts,  as parsing of the data is computationally
          expensive. Stage 2 caching is only used for some api functions.

    Most commonly, you will enable caching right at the beginning of your script:

        >>> import fastf1
        >>> fastf1.Cache.enable_cache('path/to/cache')  # doctest: +SKIP
        # change cache directory to an exisitng empty directory on your machine
        >>> session = fastf1.get_session(2021, 5, 'Q')
        >>> # ...

    Note that you should always enable caching except for very rare
    circumstances which are usually limited to doing core developement
    on FastF1.
    """
    _CACHE_DIR = ''
    _API_CORE_VERSION = 6  # version of the api parser code (unrelated to release version number)
    _IGNORE_VERSION = False
    _FORCE_RENEW = False

    _requests_session = None
    _has_been_warned = False  # flag to ensure that warning about disabled cache is logged once only
    _tmp_disabled = False

    @classmethod
    def enable_cache(cls, cache_dir, ignore_version=False, force_renew=False, use_requests_cache=True):
        """Enables the API cache.

        Args:
            cache_dir (str): Path to the directory which should be used to store cached data. Path needs to exist.
            ignore_version (bool): Ignore if cached data was create with a different version of the API parser
                (not recommended: this can cause crashes or unrecognized errors as incompatible data may be loaded)
            force_renew (bool): Ignore existing cached data. Download data and update the cache instead.
            use_requests_cache (bool): Do caching of the raw GET and POST requests.
        """
        if not os.path.exists(cache_dir):
            raise NotADirectoryError("Cache directory does not exist! Please check for typos or create it first.")
        cls._CACHE_DIR = cache_dir
        cls._IGNORE_VERSION = ignore_version
        cls._FORCE_RENEW = force_renew
        if use_requests_cache:
            cls._requests_session = requests_cache.CachedSession(
                cache_name=os.path.join(cache_dir, 'fastf1_http_cache'),
                backend='sqlite',
                allowable_methods=('GET', 'POST'),
                expire_after=datetime.timedelta(hours=12),
                cache_control=True,
                stale_if_error=True
            )
            if force_renew:
                cls._requests_session.cache.clear()

    @classmethod
    def requests_get(cls, *args, **kwargs):
        """Wraps `requests.Session().get()` with caching if enabled.

        All GET requests that require caching should be performed through this
        wrapper. Caching will be done if the module-wide cache has been
        enabled. Else, `requests.Session().get()` will be called without any
        caching.
        """
        cls._show_not_enabled_warning()
        if (cls._requests_session is None) or cls._tmp_disabled:
            return requests.get(*args, **kwargs)
        return cls._requests_session.get(*args, **kwargs)

    @classmethod
    def requests_post(cls, *args, **kwargs):
        """Wraps `requests.Session().post()` with caching if enabled.

        All POST requests that require caching should be performed through this
        wrapper. Caching will be done if the module-wide cache has been
        enabled. Else, `requests.Session().get()` will be called without any
        caching.
        """
        cls._show_not_enabled_warning()
        if (cls._requests_session is None) or cls._tmp_disabled:
            return requests.post(*args, **kwargs)
        return cls._requests_session.post(*args, **kwargs)

    @classmethod
    def clear_cache(cls, cache_dir, deep=False):
        """Clear all cached data.

        This deletes all cache files in the provided cache directory.
        Optionally, the requests cache is cleared too.

        Can be called without enabling the cache first.

        Deleting specific events or sessions is not supported but can be done manually (stage 2 cache).
        The cached data is structured by year, event and session. The structure is more or less self-explanatory.
        To delete specific events or sessions delete the corresponding folder within the cache directory.
        Deleting specific requests from the requests cache (stage 1) is not possible. To delete the requests cache only,
        delete the sqlite file in the root of the cache directory.

        Args:
            cache_dir (str): Path to the directory which is used to store cached data.
            deep (bool): Clear the requests cache (stage 1) too.
        """
        if not os.path.exists(cache_dir):
            raise NotADirectoryError("Cache directory does not exist!")

        for dirpath, dirnames, filenames in os.walk(cache_dir):
            for filename in filenames:
                if filename.endswith('.ff1pkl'):
                    os.remove(os.path.join(dirpath, filename))

        if deep:
            if not hasattr(requests.Session(), 'cache'):
                cls._install_requests_cache(cache_dir)
            requests_cache.clear()

    @classmethod
    def api_request_wrapper(cls, func):
        """Wrapper function for adding stage 2 caching to api functions.

        Args:
            func: function to be wrapped

        Returns:
            The wrapped function
        """
        @functools.wraps(func)
        def _cached_api_request(api_path, response=None, livedata=None):
            if cls._CACHE_DIR and not cls._tmp_disabled:
                # caching is enabled
                func_name = str(func.__name__)
                cache_file_path = cls._get_cache_file_path(api_path, func_name)

                if os.path.isfile(cache_file_path):
                    # file exists already, try to load it
                    try:
                        cached = pickle.load(open(cache_file_path, 'rb'))
                    except:  # noqa: E722 (bare except)
                        # don't like the bare exception clause but who knows
                        # which dependency will raise which internal exception
                        # after it was updated
                        cached = None

                    if cached is not None and cls._data_ok_for_use(cached):
                        # cached data is ok for use, return it
                        logging.info(f"Using cached data for {func_name}")
                        return cached['data']

                    else:
                        # cached data needs to be downloaded again and updated
                        logging.info(f"Updating cache for {func_name}...")
                        data = func(
                            api_path, response=response, livedata=livedata
                        )

                        if data is not None:
                            cls._write_cache(data, cache_file_path)
                            logging.info("Cache updated!")
                            return data

                        logging.critical(
                            "A cache update is required but the data failed "
                            "to download. Cannot continue!\nYou may force to "
                            "ignore a cache version mismatch by using the "
                            "`ignore_version=True` keyword when enabling the "
                            "cache (not recommended)."
                        )
                        exit()

                else:  # cached data does not yet exist for this api request
                    logging.info(f"No cached data found for {func_name}. "
                                 f"Loading data...")
                    data = func(
                        api_path, response=response, livedata=livedata
                    )
                    if data is not None:
                        cls._write_cache(data, cache_file_path)
                        logging.info("Data has been written to cache!")
                        return data

                    logging.critical("Failed to load data!")
                    exit()

            else:  # cache was not enabled
                if not cls._tmp_disabled:
                    cls._show_not_enabled_warning()
                return func(api_path, response=response, livedata=livedata)

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
    def _show_not_enabled_warning(cls):
        if not cls._CACHE_DIR and not cls._has_been_warned:
            # warn only once and only if cache is not enabled
            logging.warning(
                "\n\nNO CACHE! Api caching has not been enabled! \n\t"
                "It is highly recommended to enable this feature for much "
                "faster data loading!\n\t"
                "Use `fastf1.Cache.enable_cache('path/to/cache/')`\n")

            cls._has_been_warned = True

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


class _NoCacheContext:
    def __enter__(self):
        Cache.set_disabled()

    def __exit__(self, exc_type, exc_val, exc_tb):
        Cache.set_enabled()


def make_path(wname, wdate, sname, sdate):
    """Create the api path base string to append on livetiming.formula1.com for api
    requests.

    The api path base string changes for every session only.

    Args:
        wname: Weekend name (e.g. 'Italian Grand Prix')
        wdate: Weekend date (e.g. '2019-09-08')
        sname: Session name 'Qualifying' or 'Race'
        sdate: Session date (formatted as wdate)

    Returns:
        relative url path
    """
    smooth_operator = f'{wdate[:4]}/{wdate} {wname}/{sdate} {sname}/'
    return '/static/' + smooth_operator.replace(' ', '_')


# define all empty columns for timing data
EMPTY_LAPS = {'Time': pd.NaT, 'Driver': str(), 'LapTime': pd.NaT,
              'NumberOfLaps': np.NaN, 'NumberOfPitStops': np.NaN,
              'PitOutTime': pd.NaT, 'PitInTime': pd.NaT,
              'Sector1Time': pd.NaT, 'Sector2Time': pd.NaT,
              'Sector3Time': pd.NaT, 'Sector1SessionTime': pd.NaT,
              'Sector2SessionTime': pd.NaT, 'Sector3SessionTime': pd.NaT,
              'SpeedI1': np.NaN, 'SpeedI2': np.NaN, 'SpeedFL': np.NaN,
              'SpeedST': np.NaN, 'IsPersonalBest': False}

EMPTY_STREAM = {'Time': pd.NaT, 'Driver': str(), 'Position': np.NaN,
                'GapToLeader': np.NaN, 'IntervalToPositionAhead': np.NaN}


@Cache.api_request_wrapper
def timing_data(path, response=None, livedata=None):
    """Fetch and parse timing data.

    Timing data is a mixed stream of information. At a given time a packet of data may indicate position, lap time,
    speed trap, sector times and so on.

    While most of this data can be mapped lap by lap giving a readable and usable data structure (-> laps_data),
    other entries like position and time gaps are provided on a more frequent time base. Those values are separated
    and returned as a separate object (-> stream_data).

    .. note:: This function does not actually return "raw" API data. This is because of the need to process a mixed
      linear data stream into a usable object and because of frequent errors and inaccuracies in said stream.
      Occasionally an "educated guess" needs to be made for judging whether a value belongs to this lap or to another
      lap. Additionally, some values which are considered "obviously" wrong are removed from the data. This can happen
      with or without warnings, depending on the reason and severity.

      - Timestamps ('SessionTime') marking start or end of a lap are
        post-processed as the provided values are inaccurate.
      - Lap and sector times are not modified ever! They are considered as the
        absolute truth. If necessary, other values are adjusted to fit.


    Args:
        path: api path base string (usually ``Session.api_path``)
        response (optional): api response can be passed if data was already downloaded
        livedata: An instance of :class:`fastf1.livetiming.data.LiveTimingData`
            to use as a source instead of the api

    Returns:
        (DataFrame, DataFrame):

            - laps_data (DataFrame):
                contains the following columns of data (one row per driver and lap)

                    - Time (pandas.Timedelta): Session time at which the lap was set (i.e. finished)
                    - LapTime (pandas.Timedelta): Lap time of the last finished lap (the lap in this row)
                    - Driver (str): Driver number
                    - NumberOfLaps (int): Number of laps driven by this driver including the lap in this row
                    - NumberOfPitStops (int): Number of pit stops of this driver
                    - PitInTime (pandas.Timedelta): Session time at which the driver entered the pits. Consequentially,
                      if this value is not NaT the lap in this row is an inlap.
                    - PitOutTime (pandas.Timedelta): Session time at which the driver exited the pits. Consequentially,
                      if this value is not NaT  the lap in this row is an outlap.
                    - Sector1/2/3Time (pandas.Timedelta): Sector times (one column for each sector time)
                    - Sector1/2/3SessionTime (pandas.Timedelta): Session time at which the corresponding sector time
                      was set (one column for each sector's session time)
                    - SpeedI1/I2/FL/ST: Speed trap speeds; FL is speed at the finish line; I1 and I2 are speed traps in
                      sector 1 and 2 respectively; ST maybe a speed trap on the longest straight (?)

            - stream_data (DataFrame):
                contains the following columns of data

                    - Time (pandas.Timedelta): Session time at which this sample was created
                    - Driver (str): Driver number
                    - Position (int): Position in the field
                    - GapToLeader (pandas.Timedelta): Time gap to leader in seconds
                    - IntervalToPositionAhead (pandas.Timedelta): Time gap to car ahead

    Raises:
        SessionNotAvailableError: in case the F1 livetiming api returns no data
    """

    # possible optional sanity checks (TODO, maybe):
    #   - inlap has to be followed by outlap
    #   - pit stops may never be negative (missing outlap)
    #   - speed traps against telemetry (especially in Q FastLap - Slow Lap)
    if livedata is not None and livedata.has('TimingData'):
        response = livedata.get('TimingData')
    elif response is None:  # no previous response provided
        logging.info("Fetching timing data...")
        response = fetch_page(path, 'timing_data')
        if response is None:  # no response received
            raise SessionNotAvailableError(
                "No data for this session! If this session only finished "
                "recently, please try again in a few minutes."
            )
    logging.info("Parsing timing data...")

    # split up response per driver for easier iteration and processing later
    resp_per_driver = dict()
    for entry in response:
        if (len(entry) < 2) or 'Lines' not in entry[1]:
            continue
        for drv in entry[1]['Lines']:
            if drv not in resp_per_driver.keys():
                resp_per_driver[drv] = [(entry[0], entry[1]['Lines'][drv])]
            else:
                resp_per_driver[drv].append((entry[0], entry[1]['Lines'][drv]))

    # create empty data dicts and populate them with data from all drivers after that
    laps_data = {key: list() for key, val in EMPTY_LAPS.items()}
    stream_data = {key: list() for key, val in EMPTY_STREAM.items()}

    for drv in resp_per_driver.keys():
        drv_laps_data = _laps_data_driver(resp_per_driver[drv], EMPTY_LAPS, drv)
        drv_stream_data = _stream_data_driver(resp_per_driver[drv], EMPTY_STREAM, drv)

        for key in EMPTY_LAPS.keys():
            laps_data[key].extend(drv_laps_data[key])

        for key in EMPTY_STREAM.keys():
            stream_data[key].extend(drv_stream_data[key])

    laps_data = pd.DataFrame(laps_data)
    stream_data = pd.DataFrame(stream_data)

    return laps_data, stream_data


def _laps_data_driver(driver_raw, empty_vals, drv):
    """
    Data is on a per-lap basis.

    Boolean flag 'PitOut' is not evaluated. Meaning is unknown and flag is only sometimes present when a car leaves
    the pits.

    Params:
        driver_raw (list): raw api response for this driver only [(Timestamp, data), (...), ...]
        empty_vals (dict): dictionary of column names and empty column values
        drv (str): driver identifier

    Returns:
         dictionary of laps data for this driver
    """

    integrity_errors = list()

    # do a quick first pass over the data to find out when laps start and end
    # this is needed so we can work with a more efficient "look ahead" on the main pass
    # example: we can have 'PitOut' 0.01s before a new lap starts, but 'PitOut' belongs to the new lap, not the old one

    lapcnt = 0  # we're keeping two separate lap counts because sometimes the api has a non existent lap too much...
    api_lapcnt = 0  # ...at the beginning; we can correct that though;
    # api_lapcnt does not count backwards even if the source data does
    in_past = False  # flag for when the data went back in time
    out_of_pit = False  # flag set to true when driver drives out FOR THE FIRST TIME; stays true from then on

    # entries are prefilled with empty values and only overwritten if they exist in the response line
    drv_data = {key: [val, ] for key, val in empty_vals.items()}

    for time, resp in driver_raw:
        # the first three ifs are just edge case handling for the rare sessions were the data goes back in time
        if in_past and 'NumberOfLaps' in resp and resp['NumberOfLaps'] == api_lapcnt:
            in_past = False  # we're back in the present

        if 'NumberOfLaps' in resp and ((prev_lapcnt := resp['NumberOfLaps']) < api_lapcnt):
            logging.warning(f"Driver {drv: >2}: Ignoring late data for a previously processed lap."
                            f"The data may contain errors (previous: {prev_lapcnt}; current {lapcnt})")
            in_past = True
            continue

        if in_past:  # still in the past, just continue and ignore everything
            continue

        if ('InPit' in resp) and (resp['InPit'] is False):
            out_of_pit = True  # drove out of the pits for the first time

        # new lap; create next row
        if 'NumberOfLaps' in resp and resp['NumberOfLaps'] > api_lapcnt:
            api_lapcnt += 1
            # make sure the car actually drove out of the pits already; it can't be a new lap if it didn't
            if out_of_pit:
                drv_data['Time'][lapcnt] = to_timedelta(time)
                lapcnt += 1
                # append a new empty row; last row may not be populated (depending on session) and may be removed later
                for key, val in empty_vals.items():
                    drv_data[key].append(val)

    # now, do the main pass where all the other data is actually filled in
    # same counters and flags as before, reset them
    lapcnt = 0  # we're keeping two separate lap counts because sometimes the api has a non existent lap too much...
    api_lapcnt = 0  # ...at the beginning; we can correct that though;
    # api_lapcnt does not count backwards even if the source data does
    in_past = False  # flag for when the data went back in time

    personal_best_lap_time = None

    pitstops = -1  # start with -1 because first is out lap, needs to be zero after that

    # iterate through the data; new lap triggers next row in data
    for time, resp in driver_raw:
        # the first three ifs are just edge case handling for the rare sessions were the data goes back in time
        if in_past and 'NumberOfLaps' in resp and resp['NumberOfLaps'] == api_lapcnt:
            in_past = False  # we're back in the present
        if in_past or ('NumberOfLaps' in resp and resp['NumberOfLaps'] < api_lapcnt):
            in_past = True
            continue

        if (lapcnt == 0) and ((drv_data['Time'][lapcnt] - to_timedelta(time)) > pd.Timedelta(5, 'min')):
            # ignore any data which arrives more than 5 minutes before the end of the first lap, except 'PitOut'
            if ('InPit' in resp) and (resp['InPit'] is False):
                drv_data['PitOutTime'][lapcnt] = to_timedelta(time)
                pitstops = 0  # special here, can be multiple times for no reason therefore set zero instead of +=1
            continue

        # values which are up to five seconds late are still counted towards the previous lap
        # (sector times, speed traps and lap times)
        lap_offset = 0
        if (lapcnt > 0) and (to_timedelta(time) - drv_data['Time'][lapcnt - 1] < pd.Timedelta(5, 's')):
            lap_offset = 1

        if 'Sectors' in resp and isinstance(resp['Sectors'], dict):
            # sometimes it's a list but then it never contains values...
            for sn, sector, sesst in (('0', 'Sector1Time', 'Sector1SessionTime'),
                                      ('1', 'Sector2Time', 'Sector2SessionTime'),
                                      ('2', 'Sector3Time', 'Sector3SessionTime')):
                if val := recursive_dict_get(resp, 'Sectors', sn, 'Value'):
                    drv_data[sector][lapcnt - lap_offset] = to_timedelta(val)
                    drv_data[sesst][lapcnt - lap_offset] = to_timedelta(time)

        if val := recursive_dict_get(resp, 'LastLapTime', 'Value'):
            # if 'LastLapTime' is received less than five seconds after the start of a new lap, it is still added
            # to the last lap
            val = to_timedelta(val)
            if val.total_seconds() < 150:
                # laps which are longer than 150 seconds are ignored; usually this is the case between Q1, Q2 and Q3
                # because all three qualifying sessions are one session here. Those timestamps are often wrong and
                # sometimes associated with the wrong lap
                drv_data['LapTime'][lapcnt - lap_offset] = val

        if 'Speeds' in resp:
            for trapkey, trapname in (('I1', 'SpeedI1'), ('I2', 'SpeedI2'), ('FL', 'SpeedFL'), ('ST', 'SpeedST')):
                if val := recursive_dict_get(resp, 'Speeds', trapkey, 'Value'):
                    # speed has to be float because int does not support NaN
                    drv_data[trapname][lapcnt - lap_offset] = float(val)

        if 'InPit' in resp:
            # 'InPit': True is received once when entering pits, False is received once when leaving
            if resp['InPit'] is True:
                if pitstops >= 0:
                    drv_data['PitInTime'][lapcnt] = to_timedelta(time)
            elif ((('NumberOfLaps' in resp) and resp['NumberOfLaps'] > api_lapcnt)
                  or (drv_data['Time'][lapcnt] - to_timedelta(time)) < pd.Timedelta(5, 's')):
                # same response line as beginning of next lap or beginning of next lap less than 5 seconds away
                drv_data['PitOutTime'][lapcnt+1] = to_timedelta(time)  # add to next lap
                pitstops += 1
            else:
                drv_data['PitOutTime'][lapcnt] = to_timedelta(time)  # add to current lap
                pitstops += 1

        if val := recursive_dict_get(resp, 'BestLapTime', 'Value'):
            personal_best_lap_time = to_timedelta(val)

        # new lap; create next row
        if 'NumberOfLaps' in resp and resp['NumberOfLaps'] > api_lapcnt:
            api_lapcnt += 1
            # make sure the car actually drove out of the pits already; it can't be a new lap if it didn't
            if pitstops >= 0:
                drv_data['Time'][lapcnt] = to_timedelta(time)
                drv_data['NumberOfLaps'][lapcnt] = lapcnt + 1  # don't use F1's lap count; ours is better
                drv_data['NumberOfPitStops'][lapcnt] = pitstops
                drv_data['Driver'][lapcnt] = drv
                lapcnt += 1

    if lapcnt == 0:  # no data at all for this driver
        return drv_data

    # done reading the data, do postprocessing

    def data_in_lap(lap_n):
        relevant = ('Sector1Time', 'Sector2Time', 'Sector3Time', 'SpeedI1', 'SpeedI2',
                    'SpeedFL', 'SpeedST', 'LapTime')
        for col in relevant:
            if not pd.isnull(drv_data[col][lap_n]):
                return True
        return False

    # 'NumberOfLaps' always introduces a new lap (can be a previous one) but sometimes there is one more lap at the end
    # in this case the data will be added as usual above, lap count and pit stops are added here and the 'Time' is
    # calculated below from sector times
    if data_in_lap(lapcnt):
        drv_data['NumberOfLaps'][lapcnt] = lapcnt + 1
        drv_data['NumberOfPitStops'][lapcnt] = pitstops
        drv_data['Driver'][lapcnt] = drv
    else:  # if there was no more data after the last lap count increase, delete the last empty record
        for key in drv_data.keys():
            drv_data[key] = drv_data[key][:-1]
    if not data_in_lap(0):  # remove first lap if there's no data; "pseudo outlap" that didn't exist
        for key in drv_data.keys():
            drv_data[key] = drv_data[key][1:]
        drv_data['NumberOfLaps'] = list(map(lambda n: n-1, drv_data['NumberOfLaps']))  # reduce each lap count by one

    if not drv_data['Time']:
        # ensure that there is still data left after potentially removing a lap
        return drv_data

    # check for incorrect lap times and remove them
    # fixes GH#167 among others
    for i in range(len(drv_data['Time'])):
        sector_sum = datetime.timedelta(0)
        for key in ('Sector1Time', 'Sector2Time', 'Sector3Time'):
            st = drv_data[key][i]
            if pd.isna(st):
                continue
            sector_sum += st
        if sector_sum > drv_data['LapTime'][i]:
            drv_data['LapTime'][i] = pd.NaT
            integrity_errors.append(i+1)

    # lap time sync; check which sector time was triggered with the lowest latency
    # Sector3SessionTime == end of lap
    # Sector2SessionTime + Sector3Time == end of lap
    # Sector1SessionTime + Sector2Time + Sector3Time == end of lap
    # all of these three have slightly different times; take earliest one -> most exact because can't trigger too early
    for i in range(len(drv_data['Time'])):
        sector_sum = pd.Timedelta(0)
        min_time = drv_data['Time'][i]
        for sector_time, session_time in ((pd.Timedelta(0), drv_data['Sector3SessionTime'][i]),
                                          (drv_data['Sector3Time'][i], drv_data['Sector2SessionTime'][i]),
                                          (drv_data['Sector2Time'][i], drv_data['Sector1SessionTime'][i])):
            if pd.isnull(session_time):
                continue
            if pd.isnull(sector_time):
                break  # need to stop here because else the sector sum will be incorrect

            sector_sum += sector_time
            new_time = session_time + sector_sum
            if not pd.isnull(new_time) and (new_time < min_time or pd.isnull(min_time)):
                min_time = new_time
        if i > 0 and min_time < drv_data['Time'][i-1]:
            integrity_errors.append(i+1)  # not be possible if sector times and lap time are correct
            continue

        drv_data['Time'][i] = min_time

    # last lap needs to be removed if it does not have a 'Time' and it could not be calculated (likely an inlap)
    if pd.isnull(drv_data['Time'][-1]):
        if not pd.isnull(drv_data['PitInTime'][-1]):
            drv_data['Time'][-1] = drv_data['PitInTime'][-1]
        else:
            for key in drv_data.keys():
                drv_data[key] = drv_data[key][:-1]

    if not drv_data['Time']:
        # ensure that there is still data left after potentially removing a lap
        return drv_data

    # more lap sync, this time check which lap triggered with the lowest latency
    for i in range(len(drv_data['Time'])-1, 0, -1):
        if (new_time := drv_data['Time'][i] - drv_data['LapTime'][i]) < drv_data['Time'][i-1]:
            if i > 1 and new_time < drv_data['Time'][i-2]:
                integrity_errors.append(i+1)  # not be possible if sector times and lap time are correct
            else:
                drv_data['Time'][i-1] = new_time

    # need to go both directions once to make everything match up; also recalculate sector times
    for i in range(len(drv_data['Time'])-1):
        if any(pd.isnull(tst) for tst in (drv_data['Time'][i], drv_data['LapTime'][i+1], drv_data['Sector1Time'][i+1],
                                          drv_data['Sector2Time'][i+1], drv_data['Sector3Time'][i+1])):
            continue  # lap not usable, missing critical values

        if (new_time := drv_data['Time'][i] + drv_data['LapTime'][i+1]) < drv_data['Time'][i+1]:
            drv_data['Time'][i+1] = new_time
        if (new_s1_time := drv_data['Time'][i] + drv_data['Sector1Time'][i+1]) < drv_data['Sector1SessionTime'][i+1]:
            drv_data['Sector1SessionTime'][i+1] = new_s1_time
        if (new_s2_time := drv_data['Time'][i] + drv_data['Sector1Time'][i+1] + drv_data['Sector2Time'][i+1]) < \
                drv_data['Sector2SessionTime'][i+1]:
            drv_data['Sector2SessionTime'][i+1] = new_s2_time
        if (new_s3_time := drv_data['Time'][i] + drv_data['Sector1Time'][i+1] + drv_data['Sector2Time'][i+1] +
                drv_data['Sector3Time'][i+1]) < drv_data['Sector3SessionTime'][i+1]:
            drv_data['Sector3SessionTime'][i+1] = new_s3_time

    for i, time in enumerate(drv_data['LapTime']):
        if time == personal_best_lap_time:
            drv_data['IsPersonalBest'][i] = True
            break

    if integrity_errors:
        logging.warning(f"Driver {drv: >2}: Encountered {len(integrity_errors)} timing integrity error(s) "
                        f"near lap(s): {integrity_errors}")

    return drv_data


def _stream_data_driver(driver_raw, empty_vals, drv):
    """
    Data is on a timestamp basis.

    Params:
        driver_raw (list): raw api response for this driver only [(Timestamp, data), (...), ...]
        empty_vals (dict): dictionary of column names and empty column values
        drv (str): driver identifier

    Returns:
         dictionary of timing stream data for this driver
    """
    # entries are prefilled with empty or previous values and only overwritten if they exist in the response line
    # basically interpolation by filling up with last known value because not every value is in every response
    drv_data = {key: [val, ] for key, val in empty_vals.items()}
    i = 0

    # iterate through the data; timestamp + any of the values triggers new row in data
    for time, resp in driver_raw:
        new_entry = False
        if val := recursive_dict_get(resp, 'Position'):
            drv_data['Position'][i] = int(val)
            new_entry = True
        if val := recursive_dict_get(resp, 'GapToLeader'):
            drv_data['GapToLeader'][i] = val
            new_entry = True
        if val := recursive_dict_get(resp, 'IntervalToPositionAhead', 'Value'):
            drv_data['IntervalToPositionAhead'][i] = val
            new_entry = True

        # at least one value was present, create next row
        if new_entry:
            drv_data['Time'][i] = to_timedelta(time)
            drv_data['Driver'][i] = drv
            i += 1

            # create next row of data from the last values; there will always be one row too much at the end which is
            # removed again
            for key, val in empty_vals.items():
                drv_data[key].append(drv_data[key][-1])

    for key in drv_data.keys():
        drv_data[key] = drv_data[key][:-1]  # remove very last row again

    return drv_data


@Cache.api_request_wrapper
def timing_app_data(path, response=None, livedata=None):
    """Fetch and parse 'timing app data'.

    Timing app data provides the following data channels per sample:
       - LapNumber (float or nan): Current lap number
       - Driver (str): Driver number
       - LapTime (pandas.Timedelta or None): Lap time of last lap
       - Stint (int): Counter for the number of driven stints
       - TotalLaps (float or nan): Total number of laps driven on this set of tires (includes laps driven in
         other sessions!)
       - Compound (str or None): Tire compound
       - New (bool or None): Whether the tire was new when fitted
       - TyresNotChanged (int or None): ??? Probably a flag to mark pit stops without tire changes
       - Time (pandas.Timedelta): Session time
       - LapFlags (float or nan): ??? unknown
       - LapCountTime (None or ???): ??? unknown; no data
       - StartLaps (float or nan): ??? Tire age when fitted (same as 'TotalLaps' in the same sample?!?)
       - Outlap (None or ???): ??? unknown; no data

    Only a few values are present per timestamp. Somewhat comprehensive information can therefore only be obtained by
    aggregating data (usually over the course of one lap). Some values are sent even less
    frequently (for example 'Compound' only after tire changes).

    Args:
        path (str): api path base string (usually ``Session.api_path``)
        response: Response as returned by :func:`fetch_page` can be passed if it was downloaded already.
        livedata: An instance of :class:`fastf1.livetiming.data.LiveTimingData` to use as a source instead of the api

    Returns:
        A DataFrame contianing one column for each data channel as listed above.

    Raises:
        SessionNotAvailableError: in case the F1 livetiming api returns no data
    """
    if livedata is not None and livedata.has('TimingAppData'):
        response = livedata.get('TimingAppData')
    elif response is None:  # no previous response provided
        logging.info("Fetching timing app data...")
        response = fetch_page(path, 'timing_app_data')
        if response is None:  # no response received
            raise SessionNotAvailableError(
                "No data for this session! If this session only finished "
                "recently, please try again in a few minutes."
            )

    data = {'LapNumber': [], 'Driver': [], 'LapTime': [], 'Stint': [], 'TotalLaps': [], 'Compound': [], 'New': [],
            'TyresNotChanged': [], 'Time': [], 'LapFlags': [], 'LapCountTime': [], 'StartLaps': [], 'Outlap': []}

    for entry in response:
        if (len(entry) < 2) or 'Lines' not in entry[1]:
            continue

        time = to_timedelta(entry[0])
        row = entry[1]
        for driver_number in row['Lines']:
            if update := recursive_dict_get(row, 'Lines', driver_number, 'Stints'):
                for stint_number, stint in enumerate(update):
                    if isinstance(update, dict):
                        stint_number = int(stint)
                        stint = update[stint]
                    for key in data:
                        if key in stint:
                            val = stint[key]
                            if key == 'LapTime':
                                val = to_timedelta(val)
                            elif key == 'New':
                                val = True if val == 'true' else False
                            data[key].append(val)
                        else:
                            data[key].append(None)
                    for key in stint:
                        if key not in data:
                            logging.debug(f"Found unknown key in timing app data: {key}")

                    data['Time'][-1] = time
                    data['Driver'][-1] = driver_number
                    data['Stint'][-1] = stint_number

    return pd.DataFrame(data)


@Cache.api_request_wrapper
def car_data(path, response=None, livedata=None):
    """Fetch and parse car data.

    Car data provides the following data channels per sample:
        - Time (pandas.Timedelta): session timestamp (time only); inaccurate, has duplicate values; use Date instead
        - Date (pandas.Timestamp): timestamp for this sample as Date + Time; more or less exact
        - Speed (int): Km/h
        - RPM (int)
        - Gear (int): [called 'nGear' in the data!]
        - Throttle (int): 0-100%
        - Brake (bool)
        - DRS (int): 0-14 (Odd DRS is Disabled, Even DRS is Enabled) (More Research Needed)
            | 0 =  Off
            | 1 =  Off
            | 2 =  (?)
            | 3 =  (?)
            | 8 =  Detected, Eligible once in Activation Zone (Noted Sometimes)
            | 10 = On (Unknown Distinction)
            | 12 = On (Unknown Distinction)
            | 14 = On (Unknown Distinction)
        - Source (str): Indicates the source of a sample; 'car' for all values here

    The data stream has a sample rate of (usually) 240ms. The samples from the data streams for position data and
    car data do not line up. Resampling/interpolation is required to merge them.

    Args:
        path (str): api path base string (usually ``Session.api_path``)
        response: Response as returned by :func:`fetch_page` can be passed if it was downloaded already.
        livedata: An instance of :class:`fastf1.livetiming.data.LiveTimingData` to use as a source instead of the api

    Returns:
        | A dictionary containing one pandas DataFrame per driver. Dictionary keys are the driver's numbers as
          string (e.g. '16'). You should never assume that a number exists!
        | Each dataframe contains one column for each data channel as listed above

    Raises:
        SessionNotAvailableError: in case the F1 livetiming api returns no data
    """
    # data recorded from live timing has a slightly different structure
    is_livedata = False  # flag to indicate live timing data

    if livedata is not None and livedata.has('CarData.z'):
        response = livedata.get('CarData.z')
        is_livedata = True
    elif response is None:
        logging.info("Fetching car data...")
        response = fetch_page(path, 'car_data')
        if response is None:  # no response received
            raise SessionNotAvailableError(
                "No data for this session! If this session only finished "
                "recently, please try again in a few minutes."
            )

    logging.info("Parsing car data...")

    channels = {'0': 'RPM', '2': 'Speed', '3': 'nGear', '4': 'Throttle', '5': 'Brake', '45': 'DRS'}
    num_channels = ['RPM', 'Speed', 'nGear', 'Throttle', 'DRS']
    bool_channels = ['Brake']
    columns = ['Time', 'Date', 'RPM', 'Speed', 'nGear', 'Throttle', 'Brake', 'DRS', 'Source']
    ts_length = 12  # length of timestamp: len('00:00:00:000')

    data = dict()
    decode_error_count = 0

    for record in response:
        try:
            if is_livedata:
                time = to_timedelta(record[0])
                jrecord = parse(record[1], zipped=True)
            else:
                time = to_timedelta(record[:ts_length])
                jrecord = parse(record[ts_length:], zipped=True)

            for entry in jrecord['Entries']:
                # date format is '2020-08-08T09:45:03.0619797Z' with a varying number of millisecond decimal points
                # always remove last char ('z'), max len 26, right pad to len 26 with zeroes if shorter
                date = to_datetime(entry['Utc'])

                for driver in entry['Cars']:
                    if driver not in data:
                        data[driver] = {col: list() for col in columns}

                    data[driver]['Time'].append(time)
                    data[driver]['Date'].append(date)

                    for n in channels:
                        val = recursive_dict_get(entry, 'Cars', driver, 'Channels', n)
                        if not val:
                            val = 0
                        data[driver][channels[n]].append(int(val))

        except Exception:
            # too risky to specify an exception: unexpected invalid data!
            decode_error_count += 1
            continue

    if decode_error_count > 0:
        logging.warning(f"Car data: failed to decode {decode_error_count} "
                        f"messages ({len(response)} messages total)")

    # create one dataframe per driver and check for the longest dataframe
    most_complete_ref = None
    for driver in data:
        # add source reference for each sample
        data[driver]['Source'] = ['car', ] * len(data[driver]['Date'])
        data[driver] = pd.DataFrame(data[driver])  # convert dict to dataframe
        # check length of dataframe; sometimes there can be missing data
        if most_complete_ref is None or len(data[driver]['Date']) > len(most_complete_ref):
            most_complete_ref = data[driver]['Date']

    for driver in data:
        # if everything is well, all dataframes should have the same length
        # and no postprocessing is necessary
        if len(data[driver]['Date']) < len(most_complete_ref):
            # there is missing data for this driver
            # extend the Date column and fill up missing telemetry values with
            # zero, except Time which is left as NaT and will be calculated
            # correctly based on Session.t0_date anyways when creating Telemetry
            # instances in Session.load_telemetry
            index_df = pd.DataFrame(data={'Date': most_complete_ref})
            data[driver] = data[driver]\
                .merge(index_df, how='outer')\
                .sort_values(by='Date')\
                .reset_index(drop=True)

            logging.warning(f"Driver {driver: >2}: Car data is incomplete!")

        # ensure that brake data is 'boolean-compatible' in case that this is
        # ever changed
        _unique_brake_values = data[driver].loc[:, 'Brake'].unique()
        if ((_unique_brake_values > 0) & (_unique_brake_values < 100)).any():
            logging.warning(f"Driver {driver: >2}: Raw brake data contains "
                            f"non-boolean values!")

        # convert to correct datatypes
        data[driver].loc[:, num_channels] = data[driver] \
            .loc[:, num_channels]\
            .fillna(value=0, inplace=False)\
            .astype('int64')

        data[driver].loc[:, bool_channels] = data[driver] \
            .loc[:, bool_channels]\
            .fillna(value=False, inplace=False)\
            .astype('bool')

    return data


@Cache.api_request_wrapper
def position_data(path, response=None, livedata=None):
    """Fetch and parse position data.

    Position data provides the following data channels per sample:
        - Time (pandas.Timedelta): session timestamp (time only); inaccurate, has duplicate values; use Date instead
        - Date (pandas.Timestamp): timestamp for this sample as Date + Time; more or less exact
        - Status (str): 'OnTrack' or 'OffTrack'
        - X, Y, Z (int): Position coordinates; starting from 2020 the coordinates are given in 1/10 meter
        - Source (str): Indicates the source of a sample; 'pos' for all values here

    The data stream has a sample rate of (usually) 220ms. The samples from the data streams for position data and
    car data do not line up. Resampling/interpolation is required to merge them.

    Args:
        path (str): api path base string (usually ``Session.api_path``)
        response: Response as returned by :func:`fetch_page` can be passed if it was downloaded already.
        livedata: An instance of :class:`fastf1.livetiming.data.LiveTimingData` to use as a source instead of the api

    Returns:
        | A dictionary containing one pandas DataFrame per driver. Dictionary keys are the driver's numbers as
          string (e.g. '16'). You should never assume that a number exists!
        | Each dataframe contains one column for each data channel as listed above

    Raises:
        SessionNotAvailableError: in case the F1 livetiming api returns no data
    """
    # data recorded from live timing has a slightly different structure
    is_livedata = False  # flag to indicate live timing data

    if livedata is not None and livedata.has('Position.z'):
        response = livedata.get('Position.z')
        is_livedata = True
    elif response is None:
        logging.info("Fetching position data...")
        response = fetch_page(path, 'position')
        if response is None:  # no response received
            raise SessionNotAvailableError(
                "No data for this session! If this session only finished "
                "recently, please try again in a few minutes."
            )

    logging.info("Parsing position data...")

    if not response:
        return {}

    ts_length = 12  # length of timestamp: len('00:00:00:000')
    columns = ['Time', 'Date', 'Status', 'X', 'Y', 'Z', 'Source']

    data = dict()
    decode_error_count = 0

    for record in response:
        try:
            if is_livedata:
                time = record[0]
                jrecord = parse(record[1], zipped=True)
            else:
                time = to_timedelta(record[:ts_length])
                jrecord = parse(record[ts_length:], zipped=True)

            for sample in jrecord['Position']:
                # date format is '2020-08-08T09:45:03.0619797Z' with a varying number of millisecond decimal points
                # always remove last char ('z'), max len 26, right pad to len 26 with zeroes if shorter
                date = to_datetime(sample['Timestamp'])

                for driver in sample['Entries']:
                    if driver not in data:
                        data[driver] = {col: list() for col in columns}

                    data[driver]['Time'].append(time)
                    data[driver]['Date'].append(date)

                    for coord in ['X', 'Y', 'Z']:
                        data[driver][coord].append(recursive_dict_get(sample, 'Entries', driver, coord))

                    status = recursive_dict_get(sample, 'Entries', driver, 'Status')
                    if str(status).isdigit():
                        # Fallback on older api status mapping and convert
                        status = 'OffTrack' if int(status) else 'OnTrack'
                    data[driver]['Status'].append(status)

        except Exception:
            # too risky to specify an exception: unexpected invalid data!
            decode_error_count += 1
            continue

    if decode_error_count > 0:
        logging.warning(f"Position data: failed to decode {decode_error_count} "
                        f"messages ({len(response)} messages total)")

    # create one dataframe per driver and check for the longest dataframe
    most_complete_ref = None
    for driver in data:
        data[driver]['Source'] = ['pos', ] * len(data[driver]['Date'])  # add source reference for each sample
        data[driver] = pd.DataFrame(data[driver])  # convert dict to dataframe
        # check length of dataframe; sometimes there can be missing data
        if most_complete_ref is None or len(data[driver]['Date']) > len(most_complete_ref):
            most_complete_ref = data[driver]['Date']

    # if everything is well, all dataframes should have the same length and no postprocessing is necessary
    for driver in data:
        if len(data[driver]['Date']) < len(most_complete_ref):
            # there is missing data for this driver
            # extend the Date column and fill up missing telemetry values with
            # zero, except Time which is left as NaT and will be calculated
            # correctly based on Session.t0_date anyways when creating Telemetry
            # instances in Session.load_telemetry
            # and except Status which should be 'OffTrack' for missing data
            index_df = pd.DataFrame(data={'Date': most_complete_ref})
            data[driver] = data[driver]\
                .merge(index_df, how='outer')\
                .sort_values(by='Date')\
                .reset_index(drop=True)
            data[driver]['Status'].fillna(value='OffTrack', inplace=True)
            data[driver].loc[:, ['X', 'Y', 'Z']] = data[driver]\
                .loc[:, ['X', 'Y', 'Z']].fillna(value=0, inplace=False)

            logging.warning(f"Driver {driver: >2}: Position data is incomplete!")

    return data


@Cache.api_request_wrapper
def track_status_data(path, response=None, livedata=None):
    """Fetch and parse track status data.

    Track status contains information on yellow/red/green flags, safety car and virtual safety car. It provides the
    following data channels per sample:

        - Time (datetime.timedelta): session timestamp (time only)
        - Status (str): contains track status changes as numeric values (described below)
        - Message (str): contains the same information as status but in easily understandable
          words ('Yellow', 'AllClear',...)

    A new value is sent every time the track status changes.

    Track status is indicated using single digit integer status codes (as string). List of known statuses:

        - '1': Track clear (beginning of session ot to indicate the end of another status)
        - '2': Yellow flag (sectors are unknown)
        - '3': ??? Never seen so far, does not exist?
        - '4': Safety Car
        - '5': Red Flag
        - '6': Virtual Safety Car deployed
        - '7': Virtual Safety Car ending (As indicated on the drivers steering wheel, on tv and so on; status '1'
          will mark the actual end)

    Args:
        path (str): api path base string (usually ``Session.api_path``)
        response: Response as returned by :func:`fetch_page` can be passed if it was downloaded already.
        livedata: An instance of :class:`fastf1.livetiming.data.LiveTimingData` to use as a source instead of the api

    Returns:
        A dictionary containing one key for each data channel and a list of values per key.

    Raises:
        SessionNotAvailableError: in case the F1 livetiming api returns no data
    """
    if livedata is not None and livedata.has('TrackStatus'):
        # does not need any further processing
        logging.info("Loading track status data")
        return livedata.get('TrackStatus')
    elif response is None:
        logging.info("Fetching track status data...")
        response = fetch_page(path, 'track_status')
        if response is None:  # no response received
            raise SessionNotAvailableError(
                "No data for this session! If this session only finished "
                "recently, please try again in a few minutes."
            )

    data = {'Time': [], 'Status': [], 'Message': []}

    for entry in response:
        if len(entry) < 2:
            continue
        row = entry[1]
        if not isinstance(row, dict):
            continue
        data['Time'].append(to_timedelta(entry[0]))
        data['Status'].append(row.get('Status', ''))
        data['Message'].append(row.get('Message', ''))

    return data


@Cache.api_request_wrapper
def session_status_data(path, response=None, livedata=None):
    """Fetch and parse session status data.

    Session status contains information on when a session was started and when it ended (amongst others). It
    provides the following data channels per sample:

        - Time (datetime.timedelta): session timestamp (time only)
        - Status (str): status messages

    A new value is sent every time the session status changes.

    Args:
        path (str): api path base string (usually ``Session.api_path``)
        response: Response as returned by :func:`fetch_page` can be passed if it was downloaded already.
        livedata: An instance of :class:`fastf1.livetiming.data.LiveTimingData` to use as a source instead of the api

    Returns:
        A dictionary containing one key for each data channel and a list of values per key.

    Raises:
        SessionNotAvailableError: in case the F1 livetiming api returns no data
    """
    if livedata is not None and livedata.has('SessionStatus'):
        # does not need any further processing
        logging.info("Loading session status data")
        return livedata.get('SessionStatus')
    elif response is None:
        logging.info("Fetching session status data...")
        response = fetch_page(path, 'session_status')
        if response is None:  # no response received
            raise SessionNotAvailableError(
                "No data for this session! If this session only finished "
                "recently, please try again in a few minutes."
            )

    data = {'Time': [], 'Status': []}

    for entry in response:
        if len(entry) < 2:
            continue
        row = entry[1]
        if not isinstance(row, dict) or 'Status' not in row:
            continue

        data['Time'].append(to_timedelta(entry[0]))
        data['Status'].append(row['Status'])

    return data


@Cache.api_request_wrapper
def race_control_messages(path, response=None, livedata=None):
    """Fetch and parse race control messages.

    Race control messages are sent by race control to all teams to notify of
    decisions and statuses of the session.

    Every message has the following attributes:

        - Utc: Message timestamp
        - Category (str): Type of message, "Other", "Flag", "Drs", "CarEvent"
        - Message (str): Content of message

    Other possible attributes are:

        - Status (str): Status of context, e.g. "DISABLED" for disabling DRS
        - Flag (str): Type of flag being waved "GREEN", "RED", "YELLOW",
          "CLEAR", "CHEQUERED"
        - Scope (str): Scope of message "Track", "Sector", "Driver"
        - Sector (int): Affected track sector for sector-scoped messages
        - RacingNumber (str): Affected driver for CarEvent messages

    Args:
        path (str): api path base string (usually ``Session.api_path``)
        response: Response as returned by :func:`fetch_page` can be passed if
            it was downloaded already.
        livedata: An instance of
            :class:`fastf1.livetiming.data.LiveTimingData` to use as a source
            instead of the api

    Returns:
        A dictionary containing one key for each data channel and a list of
        values per key.

    Raises:
        SessionNotAvailableError: in case the F1 livetiming api returns no data
    """
    if livedata is not None and livedata.has('RaceControlMessages'):
        # does not need any further processing
        logging.info("Loading race control messages")
        return livedata.get('RaceControlMessages')
    elif response is None:
        logging.info("Fetching race control messages...")
        response = fetch_page(path, 'race_control_messages')
        if response is None:  # no response received
            raise SessionNotAvailableError(
                "No data for this session! If this session only finished "
                "recently, please try again in a few minutes."
            )

    data = {
        'Time': [], 'Category': [], 'Message': [], 'Status': [],
        'Flag': [], 'Scope': [], 'Sector': [], 'RacingNumber': []
    }
    data_keys = ('Category', 'Message', 'Status', 'Flag', 'Scope', 'Sector',
                 'RacingNumber')
    converters = (str, str, str, str, str, int, str)

    for entry in response['Messages']:
        data['Time'].append(to_datetime(entry['Utc']))

        for key, conv in zip(data_keys, converters):
            try:
                data[key].append(conv(entry[key]))
            except (KeyError, ValueError):
                # type conversion failed or key is missing
                data[key].append(None)

    return data


@Cache.api_request_wrapper
def driver_info(path, response=None, livedata=None):
    """Fetch driver information.

    Driver information contains the following information about each driver:

        `['RacingNumber', 'BroadcastName', 'FullName', 'Tla', 'Line',
        'TeamName', 'TeamColour', 'FirstName', 'LastName', 'Reference',
        'HeadshotUrl']`

    Args:
        path (str): api path base string (usually ``Session.api_path``)
        response: Response as returned by :func:`fetch_page`
            can be passed if it was downloaded already.
        livedata: An instance of :class:`fastf1.livetiming.data.LiveTimingData`
            to use as a source instead of the api

    Returns:
        A dictionary containing one entry for each driver
        with the drivers racing number as key

    Raises:
        SessionNotAvailableError: in case the F1 livetiming api returns no data
    """
    if livedata is not None and livedata.has('DriverList'):
        # does not need any further processing
        logging.info("Loading driver list")
        response = livedata.get('DriverList')
    elif response is None:
        logging.info("Fetching driver list...")
        response = fetch_page(path, 'driver_list')
        if response is None:  # no response received
            raise SessionNotAvailableError(
                "No data for this session! If this session only finished "
                "recently, please try again in a few minutes."
            )

    # search for the correct entries that contain driver/team/headshot info
    # for some sessions headshots are one entry for each team (Miami 22 FPs, Q)
    drv_idx = None
    team_idx = None
    headshots = []

    for i, entry in enumerate(response):
        if 'RacingNumber' in str(entry):
            drv_idx = i
        if 'TeamName' in str(entry):
            team_idx = i
        if 'HeadshotUrl' in str(entry):
            headshots.append(i)
        if drv_idx and team_idx:
            break

    # parse data
    try:
        drv_info = response[drv_idx][1]
    except (IndexError, TypeError):
        return dict()

    try:
        team_info = response[team_idx][1]
    except (IndexError, TypeError):
        return dict()

    # loop through headshots
    try:
        head_info = dict()
        for head in headshots:
            head_info.update(response[head][1])
    except (IndexError, TypeError):
        return dict()

    else:
        for drv in drv_info:
            drv_info[drv].update(team_info.get(drv, {}))
            drv_info[drv].update(head_info.get(drv, {}))

        if not len(drv_info) or not isinstance(drv_info, dict):
            return dict()
        if 'RacingNumber' not in list(drv_info.values())[0]:
            return dict()
        return drv_info


@Cache.api_request_wrapper
def weather_data(path, response=None, livedata=None):
    """Fetch and parse weather data.

    Weather data provides the following data channels per sample:

        - Time (datetime.timedelta): session timestamp (time only)
        - AirTemp (float): Air temperature [°C]
        - Humidity (float): Relative humidity [%]
        - Pressure (float): Air pressure [mbar]
        - Rainfall (bool): Shows if there is rainfall
        - TrackTemp (float): Track temperature [°C]
        - WindDirection (int): Wind direction [°] (0°-359°)
        - WindSpeed (float): Wind speed [km/h]

    Weather data is updated once per minute.

    Args:
        path (str): api path base string (usually ``Session.api_path``)
        response: Response as returned by :func:`fetch_page` can
            be passed if it was downloaded already.
        livedata: An instance of
            :class:`fastf1.livetiming.data.LiveTimingData`
            to use as a source instead of the api

    Returns:
        A dictionary containing one key for each data channel and a list
        of values per key.

    Raises:
        SessionNotAvailableError: in case the F1 live timing api
            returns no data
    """
    if livedata is not None and livedata.has('WeatherData'):
        # does not need any further processing
        logging.info("Loading weather data")
        response = livedata.get('WeatherData')
    elif response is None:
        logging.info("Fetching weather data...")
        response = fetch_page(path, 'weather_data')
        if response is None:  # no response received
            raise SessionNotAvailableError(
                "No data for this session! If this session only finished "
                "recently, please try again in a few minutes."
            )

    data = {
        'Time': [], 'AirTemp': [], 'Humidity': [], 'Pressure': [],
        'Rainfall': [], 'TrackTemp': [], 'WindDirection': [], 'WindSpeed': []
    }

    data_keys = ('AirTemp', 'Humidity', 'Pressure', 'Rainfall',
                 'TrackTemp', 'WindDirection', 'WindSpeed')
    converters = (float, float, float,
                  lambda v: True if v == '1' else False,  # rain: str -> bool
                  float, int, float)

    for entry in response:
        if len(entry) < 2:
            continue
        row = entry[1]
        if not isinstance(row, dict):
            continue

        data['Time'].append(to_timedelta(entry[0]))
        for key, conv in zip(data_keys, converters):
            try:
                data[key].append(conv(row[key]))
            except (KeyError, ValueError):
                # type conversion failed or key is missing
                data[key].append(conv(0))

    return data


def fetch_page(path, name):
    """Fetch data from the formula1 livetiming web api, given url base path and page name. An attempt
    to parse json or decode known messages is made.

    Args:
        path (str): api path base string (usually ``Session.api_path``)
        name (str): page name (see :attr:`pages` for all known pages)

    Returns:
        - dictionary if content was json
        - list of entries if jsonStream, where each entry again contains two elements: [timestamp, content]. Content is
          parsed with :func:`parse` and will usually be a dictionary created from json data.
        - None if request failed

    """
    page = pages[name]
    is_stream = 'jsonStream' in page
    is_z = '.z.' in page
    r = Cache.requests_get(base_url + path + pages[name], headers=headers)
    if r.status_code == 200:
        raw = r.content.decode('utf-8-sig')
        if is_stream:
            records = raw.split('\r\n')[:-1]  # last split is empty
            if name in ('position', 'car_data'):
                # Special case to improve memory efficiency
                return records
            else:
                decode_error_count = 0
                tl = 12  # length of timestamp: len('00:00:00:000')
                ret = list()
                for e in records:
                    try:
                        ret.append([e[:tl], parse(e[tl:], zipped=is_z)])
                    except json.JSONDecodeError:
                        decode_error_count += 1
                        continue
                if decode_error_count > 0:
                    logging.warning(f"Failed to decode {decode_error_count}"
                                    f" messages ({len(records)} messages "
                                    f"total)")
                return ret
        else:
            return parse(raw, is_z)
    else:
        return None


def parse(text, zipped=False):
    """Parse json and jsonStream as returned by livetiming.formula1.com

    This function can only pass one data entry at a time, not a whole response.
    Timestamps and data need to be separated before and only the data must be passed as a string to be parsed.

    Args:
        text (str): The string which should be parsed
        zipped (bool): Whether or not the text is compressed. This is the case for '.z' data (e.g. position data=)

    Returns:
        Depending on data of which page is parsed:
            - a dictionary created as a result of loading json data
            - a string
    """
    if text[0] == '{':
        return json.loads(text)
    if text[0] == '"':
        text = text.strip('"')
    if zipped:
        text = zlib.decompress(base64.b64decode(text), -zlib.MAX_WBITS)
        return parse(text.decode('utf-8-sig'))
    logging.warning("Couldn't parse text")
    return text


class SessionNotAvailableError(Exception):
    """Raised if an api request returned no data for the requested session.
    A likely cause is that the session does not exist because it was cancelled."""
    def __init__(self, *args):
        super().__init__(*args)
