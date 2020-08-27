=========
Changelog
=========

v2.0.2: API code overhaul
==========================
This version integrates a major overhaul of the api code (:mod:`fastf1.api`)

- Possibly breaking changes:
    - Renamed dataframe column 'LastLapTime' to 'LapTime' for the dataframe returned by :func:`api.timing_data`
        First, this makes more sense.
        Second, this column is currently already renamed to 'LapTime' later and already accessible under this name
        in the dataframe returned by :func:`core.Session.load_laps`.

        (also applies to the dictionary returned by :func:`api._laps_data_driver`)

    - Data types in dataframes may have changed

    - Some internal functions (prefixed by '_') may have a different name, parameters and return value now

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