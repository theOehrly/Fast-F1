=========
Changelog
=========

v2.3.0
======

Bug Fixes:

  - The matplotlib dependency version is now required to be >= 3.3.3 to prevent
    incompatibility. (#210)

  - Fixed: NaT values for 'Time' or 'LapStartTime' may cause a crash
    in :func:`fastf1.core.Telemetry.calculate_driver_ahead` (#151)

  - Fixed: Data for speed trap 'SpeedST' is added to the wrong lap.
    This additionally caused empty laps to exist for some drivers at the
    beginning of some sessions.

  - Fixed: :func:`fastf1.core.Telemetry.add_driver_ahead` could not
    be called on previously resampled telemetry data. (#178)

  - Added: Better error handling for sessions that did not take place.

  - Fixed: Tyre compound shown for some laps was incorrect in some special
    cases. (#204)

  - Fixed: Incorrect first and last name for Hulkenberg in fallback driver list
    (by @niallmcevoy)

  - Fixed: metadata for :class:`~fastf1.core.Telemetry` was not propagated
    correctly in :func:`fastf1.core.Telemetry.merge_channels` and
    :func:`fastf1.core.Telemetry.resample_channels`.

  - Fixed: incorrect call of scipy method in
    :func:`fastf1.legacy.inject_driver_ahead`

  - Fixed: Error handling regression in :func:`fastf1.core.Session.load`

  - Fixed: :exc:`~fastf1.core.DataNotLoadedError` not raised for `car_data` and
    `pos_data`.


New Features:

  - Added: Function :func:`fastf1.get_events_remaining` (by @oscr)

  - Added: Support for shorthand paths (e.g. '~/cache') in
    :func:`fastf1.Cache.enable_cache` (by @oscr)


Changes:

  - The default base url scheme for Ergast is changed from http to https.


Deprecations and Notices for Upcoming Changes:

  - Deprecation: Undocumented function :func:`fastf1.ergast.fetch_weekend`
    will be removed without a direct replacement in a future version
    (target: v3.0.0).

  - Change: :func:`fastf1.utils.to_timedelta` and
    :func:`fastf1.utils.to_datetime` will return `NaT` instead of raising and
    exception if a valued cannot be parsed in a future version
    (target: v3.0.0).


v2.2.9
======

Bug Fixes:

    - Fix a typo in :attr:`fastf1.plotting.DRIVER_TRANSLATE` (#207)


v2.2.8
======

Bug Fixes:

  - Ensure that :attr:`fastf1.core.Session.drivers` returns a list of
    unique values. This prevents problems that result from drivers being
    incorrectly listed multiple times in the session result information.
    (see #182 for example)


v2.2.7
======

Bug Fixes:

    - Fixed an issue that prevented merging of car data and position data
      in some cases (see #180)


v2.2.6
======

Bug Fixes:

  - Fixed incorrect lap start times for first lap after a red flag restart

  - Fixed first lap missing if a driver crashed during the first lap of a
    sprint race (#175)

  - Fixed headshot url missing from result of :func:`fastf1.api.driver_info`
    (by @bruzie in #173)

New Features:

  - Added a check detect and to remove incorrect lap times in the api parser
    (#167)


v2.2.5
======

Bug Fixes:

  - Fixed grid position, position and points missing from Sprint sessions
    result in 2022 (#166)


New Features:

  - Added :func:`fastf1.plotting.driver_color` to get driver colors which are
    similar to the team color but slightly different between both drivers of
    one team. This ways the drivers can be differentiated better.
    (by @dialtone in #159)

  - Added support for loading race control messages, see
    :attr:`fastf1.core.Session.race_control_messages`
    (by @bruzie in #163)


v2.2.4
======

Bug Fixes:

  - compatibility fixes for supporting 'Sprint' sessions for the 2022 season
    (see also #160)


v2.2.3
======

Bug Fixes:

  - Fixed crash in :func:`fastf1.Telemetry.calculate_driver_ahead` in case
    of missing car data (#146)


v2.2.2
======

Changes:

  - Implement support for reading information about a drivers personal best
    lap from the api. :func:`~fastf1.core.Laps.pick_fastest` will now by
    default return the quickest lap that is also marked as personal best lap
    of any driver. This fixes the long standing problem that the fastest lap
    returned by this function may actually be a deleted lap.


Bug Fixes:

  - Fixed: data for the 2022 Saudi Arabian Grand Prix can not be loaded (#135)
  - Fixed: incorrect python version check in live timing client, that
    prevented running on actually supported versions of python (#132)



v2.2.1
======

Changes:

  - Log ergast error tracebacks on level DEBUG instead of WARNING to avoid
    confusion when a failure was to be expected.

Bug Fixes:

  - Fixed: no session results for Verstappen (driver number 1 vs 33)
    (by @vlesierse)
  - Fixed: slicing telemetry by using multiple laps as a reference returns no
    data if some laps have NaT values for 'Time' or 'LapStartTime'
  - Fixed regression: Loading of livetiming no longer possible since v2.2.0 if
    recording does not contain a driver list


v2.2.0
======

This release introduces a range of new features, bug fixes and improvements.
While backwards compatibility has been kept in mind, some breaking changes
are required.


Changes and New Features:

  - New :class:`fastf1.events.EventSchedule`: The event schedule provides
    information about session start times, event format, name and location of
    upcoming events as well as previous event. The schedule data for the
    current season is pulled from an external source that is updated regularly.
    This should solve issues caused by schedule changes during the seasons
    or even during a race weekend.

  - New :class:`fastf1.events.Event`: This object represents a single event
    and holds the same information as the event schedule, but for individual
    events.

  - New methods :meth:`fastf1.get_testing_session`,
    :meth:`fastf1.get_event`, :meth:`fastf1.get_testing_event` and
    :meth:`fastf1.get_event_schedule`

  - The cache now implements better automatic cache control and is used for
    all requests throughout FastF1.

  - The combination of improved caching and the implementation of the new
    event schedule now allow fastf1 to be used even if the Ergast API is not
    accessible. This improves reliability in case of temporary server or
    network problems.

  - Full offline support: Scripts can be run offline if they have been run
    at least once with an active internet connection and caching enabled.

  - Introduces the new objects :class:`fastf1.core.SessionResults` and
    :class:`fastf1.core.DriverResult`. These classes are built on top of
    :class:`pandas.DataFrame` and :class:`pandas.Series`. They provide
    information about all drivers that participated in a session.
    This information includes driver numbers, names, team names, finishing
    results, ...
    Session results are available for all sessions supported by the
    Ergast database.

  - A hard coded list of drivers is no longer required for testing sessions.
    This data can now be pulled from the api as well.

  - A more understandable error will be raised if properties of the
    :class:`~fastf1.core.Session` object are accessed which are not yet
    available because the relevant data has not been loaded.


Bug Fixes:

  - Fixed a bug that caused rain fall to always be true in weather data (#76)


Breaking Changes:

  - For **testing events**, :class:`fastf1.core.Session` objects can no longer be
    created through :func:`fastf1.get_session`. You need to use
    :func:`fastf1.get_testing_session` instead.

  - :attr:`fastf1.core.Session.date` is now a :class:`pandas.Timestamp`
    instead of a string.

  - The signature ``fastf1.core.Session.__init__(weekend, session_name)``
    has been changed to
    ``fastf1.core.Session.__init__(event, session_name)`` to adhere to
    new naming conventions. This is a breaking change if the arguments are
    given as keyword arguments.

  - :func:`fastf1.get_session` may return a different session now for some
    edge cases, if you load sessions by name instead of by round number.

  - The property :attr:`fastf1.core.Session.results` is now an instance of
    :class:`fastf1.core.SessionResults` instead of :class:`dict`. Most of the
    previously available data is accessible through the new data replacement
    object. Some special information like GPS coordinates and altitude are no
    longer available though. If you think that this data should still be
    provided by FastF1 in the future, please open an issue for that.

  - The datatype of the telemetry 'Brake' data channel is changed from
    ``int`` to ``bool``, as brake data was never actually more accurate
    than this. The representation as integer (percentage) values was
    misleading.


Deprecations:

  (Objects, methods and attributes deprecated in v2.2 will be removed
  in v2.3. Until then, accessing them will still work but a FutureWarning
  is shown, reminding you of the deprecation.)
  **Removal has been delayed for user convenience and because
  there exist no problems currently which make a removal immediately necessary.
  The new removal target is v3.0.0**


  - :class:`fastf1.core.Weekend` has been replaced with
    :class:`fastf1.events.Event`. All previously available methods and
    properties are implemented by the replacement object, although they have
    been partially deprecated.

  - The attributes ``name``, ``date`` and ``gp`` of
    :class:`fastf1.core.Weekend` have been deprecated.
    The replacement object :class:`fastf1.events.Event` subclasses
    :class:`pandas.Series`. The standard ways for accessing pandas Series'
    values should be used. The attributes have been additionally renamed in
    their Series representation.
    For example:

      - ``Weekend.name`` --> ``Event.EventName`` or ``Event['EventName']``
      - ``Weekend.date`` --> ``Event.EventDate`` or ``Event['EventDate']``
      - ``Weekend.gp`` --> ``Event.RoundNumber`` or ``Event['RoundNumber']``

  - The attribute :attr:`fastf1.core.Session.weekend` has been replaced by
    :attr:`fastf1.core.Session.event` to adhere to new naming conventions.

  - The function :func:`fastf1.core.get_round` has been deprecated and will be
    removed without replacement in v2.3. Use :func:`fastf1.get_event`
    instead and and get the round number from the returned event object.

  - :func:`fastf1.core.Session.load_laps` has been deprecated. Use
    :func:`fastf1.core.Session.load` instead, which offers more flexibility
    for deciding which data should be loaded. The new method will no longer
    return a :class:`~fastf1.core.Laps` object! You should access the
    :class:`~fastf1.core.Laps` object through
    :attr:`fastf1.core.Session.laps`

  - :class:`fastf1.core.Driver` has been replace with
    :class:`fastf1.core.DriverResult` which has a different signature.

  - The attributes ``grid``, ``position``, ``name``, ``familyname`` and
    ``team`` of :class:`fastf1.core.Driver` have been deprecated.
    The replacement object :class:`fastf1.core.DriverResult` subclasses
    :class:`pandas.Series`. The standard ways for accessing pandas Series'
    values should be used. The attributes have been additionally renamed in
    their Series representation.
    For example:

      - ``Driver.name`` --> ``DriverResult.FirstName`` or
        ``DriverResult['FirstName']``
      - ``Driver.familyname`` --> ``DriverResult.LastName`` or
        ``DriverResult['LastName']``
      - ``Driver.team`` --> ``DriverResult.TeamName`` or
        ``DriverResult['TeamName']``
      - ``Driver.grid`` --> ``DriverResult.GridPosition`` or
        ``DriverResult['GridPosition']``
      - ``Driver.position`` --> ``DriverResult.Position`` or
        ``DriverResult['Position']``



v2.1.13 More Bug Fixes
======================

- fixed issue #74: don't assume that a further session status change
  (e.g. ended, finalized) exists after the last lap
- improved error handling if there exists no usable lap data for any
  driver (#73, e.g. Imola 2021 FP1)
- :func:`fastf1.core.get_session` should not quietly return
  :class:`fastf1.core.Weekend` instead of :class:`fastf1.core.Session`
  if an invalid event name is given.


v2.1.12 Fixes and Patches
=========================

- fix: crash in lap data parser if a driver did not do any proper laps in a
  session
- fix: crash in :func:`fastf1.core.Telemetry.calculate_driver_ahead` if a
  driver did not participate in the session (by @bambz96)
- enable automatic cache expiration for requests-cache (#57)
- fix: requests cache not cleared if `force_renew=True` is used with
  :func:`fastf1.api.Cache.enable_cache`


v2.1.11 Fixes and Patches
=========================

- Fix: last inlap missing from ``Laps``
- Add schedule patch for Sprint Race Weekend at Brazil GP


v2.1.10 Ergast compatibility
============================

- introduce a custom user agent to identify FastF1 when requesting data from the Ergast API


v2.1.9 General maintenance
==========================

- switch renamed dependency 'fuzzywuzzy' to new name 'thefuzz'
- add support for getting team colors from incomplete or partial team
  names or from team names containing typos or extra words
- make fuzzy string matching for event names case-insensitive
- set missing lap start times to pit out time where possible (fixes issue #29),
- add new api function :func:`fastf1.api.driver_info`
- support incomplete laps (not timed) caused by drivers crashing/retiring
  during a lap: infer as much information as possible so that telemetry
  can be accessed easily (fixes issues #36 and #41)


v2.1.8 Add temporary support for sprint qualifying
==================================================

- This release adds a temporary patch to support weekends with sprint
  sprint qualifying and their changed order of sessions.
  To get data for sprint qualifying, you can use the ``fastf1.get_session``
  function with the argument ``event='SQ'``.
  Also remember that FP2 is on a Saturday on these weekends. FP3 does
  not exist.


v2.1.7 Various bug fixes
========================

- fix crash when loading cached data after dependencies have been updated
- specify minimum versions for pandas and numpy
- fix incorrect Alpine team name
- fix future warnings and deprecation warnings caused by Pandas 1.3.0


v2.1.6 Added weather data, general improvements and bug fixes
=============================================================

- Add weather data (#26)
  See: :meth:`.core.Lap.get_weather_data`, :meth:`.core.Laps.get_weather_data`,
  :attr:`.core.Session.weather_data`
- Fix: error when calling :meth:`.core.Laps.get_pos_data` (#22)
- Fix: error when calling `get_telemetry` on the first lap (or a set of laps
  containing the first lap)
- Make the live timing client exit more cleanly


v2.1.5 Improved robustness and minor fixes
==========================================

- Make the data parsing in :class:`fastf1.livetiming.data.LiveTimingData` more
  robust and tolerant against unexpected data.

- some more small improvements regarding logging and other stuff


v2.1.4 Bug fixes and various minor improvements
===============================================

- Fix a bug introduced in v2.1.3 which prevented the loading of
  any data from the api

- Make the api parser more robust and tolerant against invalid data

- various small improvements


v2.1.3 Improved error handling
==============================

Added error handling for partially invalid data when loading car data
and position data.


v2.1.2 Hotfixes for loading live timing data
============================================

- Fix failure to load live timing data due to an error in the
  api cache function wrapper.

- Improve track status loading


v2.1.1 Add support for recording and using live timing data
===========================================================

- Possibly breaking changes:

  - :meth:`fastf1.Session.load_laps`: Data will now be loaded without
    telemetry by default, i.e. only timing data is loaded.
    Telemetry data is usually not available anyways, therefore this prevents
    a confusing error.

- Changes:

  - Possibility to record live timing data
  - Possibility to use recorded live timing data as a data source


v2.1: Refactoring, accuracy improvements and a more accessible interface
==========================================================================

- Possibly breaking changes:

  - The 'Space' column has been renamed to 'Distance' as this makes more sense

  - :func:`fastf1.utils.delta_time` now returns two values; see explanation in the documentation

  - Lap telemetry is no longer precalculated and no longer saved in a separate column of the :class:`Laps` DataFrame.
    This telemetry is now a computed property of :class:`Laps` and :class:`Lap`

    - calculated property `.telemetry`: This contains position and car data merged into one instance of
      :class:`Telemetry` (instance of `DataFrame`). The data is comparable to the previous 'telemetry' column.
      This data is intended for easy plotting. It should not be used for any further calculations as it
      contains interpolated values.

      .. code-block::

        laps = session.load_laps()
        fastest = laps.pick_fastest()

        tel = fastest['telemetry']  # will now fail as telemetry is no longer saved in DataFrame/Series
        tel = fastest.telemetry  # will (still) work as this now accesses the computed property

    - function `get_car_data`, `get_pos_data`: These functions are available for :class:`Lap` and :class:`Laps`.
      They return the telemetry data as received from the api with minimal postprocessing and crucially
      unmerged and without any interpolated values. This data should be used if you intend to do any further
      calculations with it.

      Also read the new documentation section about doing accurate calculations: :doc:`howto_accurate_calculations`

  - Patches and color scheme changes which were automatically applied when importing :mod:`fastf1.plotting`
    now need to be enabled explicitly. This is done by calling :func:`fasf1.plotting.setup_mpl`.
    This function offers configuration through keyword arguments. The defaults are equal to what was done
    automatically before.
    It is highly recommended that you call this function to set up your matplotlib plotting environment.

  - The formatting of timedelta values in matplotlib plots is now handled by an external module called 'Timple'.
    As part of this change, the function :func:`fastf1.plotting.laptime_axis` has been removed. Timedelta data
    is now detected automatically if matplotlib timedelta support is enabled through :func:`fastf1.plotting.setup_mpl`.
    This will hopefully make the plotting of timedelta values considerably more reliable.

  - The computed telemetry channels 'Distance' (before: 'Space'), 'DriverAhead' and 'DistanceToDriverAhead' are no
    longer added to the telemetry data by default. This is done for speed and accuracy reasons. These channels can now
    be added by calling the appropriate :meth:`Telemetry.add_*` methods of the new :class:`fastf1.core.Telemetry` class.

  - The cache has been completely rewritten. It is now fully supported again and can detect version updates which
    require updating the cached data.
    Enabling the cache is now done using :func:`fastf1.api.Cache.enable_cache`



- Changes:
  - Accuracy improvement: Changes to some parts of the general flow of processing data to reduce calculation errors

  - Accuracy improvement: slightly better determination of the time at which a lap starts

  - Speed improvement: Faster parsing of API data

  - Added track status information to laps data

  - Added lap accuracy validation as a boolean 'IsAccurate' value for each lap. This is set based on track status,
    availability of some required lap data, pit stops

  - Added 'Source' to telemetry data to indicate whether a value is original ('car' or 'pos' depending on source)
    or interpolated

  - Added the class :class:`fastf1.core.Lap` which subclasses :class:`pd.Series`. :class:`Lap` is now the result of
    slicing :class:`fastf1.core.Laps`.

  - Added additional `pick_*()` functions to :class:`fastf1.core.Laps`

  - Added :class:`fastf1.core.Telemetry` which subclasses :class:`pd.DataFrame`. This class offers various methods
    for working with the telemetry data and should make it easier to work with the data. Previously inaccessible
    functionality is now accessible in a more DataFrame-like style.

  - Added various slicing capabilities for :class:`fastf1.core.Telemetry`

  - Telemetry data can be sliced at any point and calculated telemetry channels (Distance, Driver Ahead, ...)
    can be added to this slice specifically.

    Example usages:

      - 'Distance' can be calculated continuously over multiple laps (starts at zero on the first lap
        and increases all the time).

      - 'DriverAhead' can now be calculated for small telemetry slices more efficiently

  - DistanceToDriverAhead is reimplemented and returns a considerably smoother result now. This is at the cost of
    increasing integration error when used over longer periods of time (i.e. over multiple laps). To work around this,
    it should be applied to laps individually. Additionally, the old implementation is still available in
    :mod:`fastf1.legacy`.

  - Add a SignalR client for receiving and saving live timing and telemetry data during a session.


- Fixed:
  - fix: SessionNotAvailableError is now raised as Exception instead of BaseException

  - fix a crash when there is no valid car telemetry data at all (2019, Australia, FP3)

  - fix a crash caused by the resampling progressbar when there are very few laps in a session (2019, Azerbaijan, FP1)

  - fix a crash in _inject_position when some telemetry data is missing (2019, Silverstone, FP1)

  - fix a crash when data for a session can be requested but the data does not contain any useful values at
    all (2020, Styria, 'FP3')


v2.0.2: API code overhaul
==========================
This version integrates a major overhaul of the api code (:mod:`fastf1.api`)

- Possibly breaking changes:

  - Renamed dataframe column 'LastLapTime' to 'LapTime' for the dataframe returned by :func:`api.timing_data`
    First, this makes more sense.
    Second, this column is currently already renamed to 'LapTime' later and already accessible under this name
    in the dataframe returned by :func:`core.Session.load_laps`. Therefore the renaming makes the column name
    be consistend between api and core.

    (This also applies to the dictionary returned by the private function :func:`api._laps_data_driver`),

  - Data types in dataframes may have changed

  - Some private functions (prefixed by '_') may have a different name, parameters and return value now

- Changes:
  - rewrote large parts of :mod:`fastf1.api` with a somewhat cleaner implementation

    - more stability

    - better/more correct PitIn/PitOut and general lap data in some sessions (was missing last lap sometimes but had
      a first lap that didn't actually exist

    - api.timing_data and thereby also session.load_laps will raise api.SessionNotAvailableError
      if the api request returned no data. This usually happens if the session never took place because it was cancelled.

    - Attempted to fix a bug where timing data from two sources can not be merged. This is caused by the received API
      data going backwards in time by one lap. This causes data to be added to the wrong lap.
      This problem was the reason for having patch files for some drivers/sessions. The patch files have now been
      removed as they are no longer necessary.

    - improved documentation a bit

  - light cleanup and light documentation improvements of :mod:`fastf1.core`

  - supressed python-levenshtein warning; it is really not necessary to have it installed for this module

  - changed logging format for hopefully better readability

  - tried to fix lap time axis again; hopefully this time I got it right



v2.0.1: Integration of a newer version of Ax6's old repository
==============================================================
This integrates a more recent version of the old repository.
See Issue #1

- Possibly breaking changes
  - :mod:`fastf1.plotting`: access to team colors changed

    use new function :func:`fastf1.plotting.team_color`

  - :mod:`fastf1.core.Laps`: :func:`pick_driver_number` and :func:`pick_driver_numbers` have been removed.

    :func:`fastf1.core.Laps.pick_driver` and :func:`fastf1.core.Laps.pick_drivers` do now accept driver numbers a drivers'
    three letter identifiers. Number and letter identifiers can be mixed in a single function call.

- Changes:

  - An error that previously resulted in the loading of laps failing completely is now handled slightly better.
    Data loading will now only fail for a driver which is actually concerned by this error and not for all drivers.

    See: https://github.com/theOehrly/Fast-F1/issues/1#issuecomment-670712178
    This still needs to be fixed properly at some point.

  - Fix crash if cache dir does not exist

  - Some under the hood cleanups and improvements

  - Somewhat improved documentation

- New:

  - :func:`fastf1.utils.delta_time` for comparing lost/gained time between two drivers

  - manual patch file for Bottas in testing

v2.0.0: first release of this fork
==================================
- Changes:

  - fixed a bug where pandas.DataFrame functionality did not properly work with
    the `Laps class`

  - additional fixes for some minor bugs in `core.get_session`

- New:

  - `track`: module for track and track position related stuff

  - `experimental.syncsolver`: an attempt at better data synchronization



v1.5.1: last release by Ax6
=============================