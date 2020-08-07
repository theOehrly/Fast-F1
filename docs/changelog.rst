=========
Changelog
=========


v2.0.1: integration of a newer version of Ax6's old repository
==============================================================
This integrates a more recent version of the old repository.
See Issue #1

Possibly breaking change:
    - `fastf1.plotting`: access to team colors changed; use new function `team_color()`



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