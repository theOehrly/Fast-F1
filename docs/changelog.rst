=========
Changelog
=========


v2.0.1: integration of a newer version of Ax6's old repository
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