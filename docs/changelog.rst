=========
Changelog
=========


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