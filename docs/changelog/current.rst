What's new in v3.9.0
--------------------------

(released 24/10/2026)


Formula 1 Account Requirement
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

FastF1 now supports login with an F1TV Access account (or higher plan).
This became necessary after Formula 1 added a requirement for authentication
to their data APIs in October 2026.

FastF1 provides a native sign in where user credentials can be provided
interactively in the terminal while running a script, via environment
variables or by authenticating via a CLI.
A second sign in option allows sign in via a browser and requires a the
FastF1 Companion browser addon to be installed.

Login tokens are stored locally but user credentials are never stored by
FastF1. Login tokens usually expire after four days, requiring a new sign
in to fetch a new token.


Behaviour Changes
^^^^^^^^^^^^^^^^^

- Changes to ``Session.results`` for Qualifying and Sprint Qualifying (#957):
    - If a driver was eliminated in Q1 and did not pass the 107% rule, their
      best Q1 time will now be **included** in the result.
    - The "ClassifiedPosition" column will be populated with the drivers'
      respective classified positions. If a driver was eliminated in Q1, the
      value will be set to "N" for "Not Classified".
    - The old behaviour was for the "ClassifiedPosition" column to not be
      used. Drivers who failed the 107% rule had their time excluded from the
      results. The new behaviour follows partially from a change in the data
      that is returned by the Jolpica-F1 API. Further, the new behaviour
      provides more informative data and better matches the behaviour that
      was already described in the documentation.

- Updated internal rate limits for Jolpica-F1 to match changed server
  side limits.

- Improved fuzzy matching and error handling when using ``get_session``
  and ``get_event``. When match for a given event name is found with
  sufficient confidence, a ``FuzzyMatchError`` is now raised. (#862)


Bug Fixes
^^^^^^^^^

- Fixed a bug where ``Laps.iterlaps`` could raise a ``TypeError`` when
  the ``require`` argument was provided. (#958) by @VforVitorio

- Lap times >150 seconds are now allowed by the parser if the lap time
  matches the sum of all sector times. This fixes a range of missing lap time
  values in some sessions. (#956) by @kingjaiteh


New Features
^^^^^^^^^^^^

- ``SessionResults`` now includes ``Time`` (best lap time) and ``Position``
  for practice sessions ('Practice 1', 'Practice 2', 'Practice 3').
  Previously, both columns were ``NaT``/``NaN`` for these sessions.
  (#929) by @arpan2004

- The new method ``Cache.configure`` replaces ``Cache.enable_cache``. All
  arguments are keyword arguments and all of them are optional, so that
  individual cache settings can be changed easily. This also add the option to
  change settings while keeping the default cache location.

- ``Cache.disabled`` and ``Cache.set_disabled`` now accept the keyword
  arguments ``disable_http_cache`` and ``disable_func_cache``. This makes it
  possible to disable the HTTP cache (stage 1) and the parsed-data cache
  (stage 2) separately. By default, both are disabled, as before.


Deprecations
^^^^^^^^^^^^

- ``fastf1.utils.recursive_dict_get``, ``fastf1.utils.to_datetime`` and
  ``fastf1.utils.to_timedelta`` are deprecated. They were never intended to
  be part of the public API and will be removed in a future release (#884).

- The ``round`` keyword argument of ``EventSchedule.get_event_by_round`` is
  deprecated and will be removed in a future version. Use ``round_number``
  instead. (#890)

- ``Cache.enable_cache`` is deprecated and will be removed in a future
  version. Use ``Cache.configure`` instead.

- ``Cache.ci_mode`` is deprecated and will be removed in a future version. Use
  ``Cache.offline_mode`` instead.


Removals
^^^^^^^^

- The deprecated function ``fastf1.utils.delta_time`` has been removed. It
  was deprecated in v3.0.0 because it produced inaccurate results (#884).


Increased minimum versions for dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- The minimum supported version of ``requests-cache`` is now 1.3.0.
