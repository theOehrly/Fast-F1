What's new in v3.8.1
--------------------

(released 11/02/2026)


Bug Fixes
^^^^^^^^^

- Patches to support 2026 Pre-Season Testing



What's new in v3.8.0
--------------------

(released 10/02/2026)


Dependency Changes
^^^^^^^^^^^^^^^^^^

- Support for Python 3.9 is dropped. Python 3.10 is the new minimum version.

- Pydantic is added as a new dependency.

- The minimum required versions for selected dependencies are increased as follows:

  - matplotlib>=3.8.0
  - numpy>=1.26.0
  - pandas>=2.1.1
  - requests>=2.30.0
  - scipy>=1.11.0


New Features
^^^^^^^^^^^^

- Missing speed trap values are now filled in by FastF1 when possible (#834).

- A new submodule ``fastf1.exceptions`` is introduced. This submodule contains all public
  custom exceptions going forward. Importing exceptions from other parts of FastF1 is deprecated.

- FastF1 is now able to auto-generate (with limitations) team name and color constants that are
  required for full functionality of the ``fastf1.plotting`` submodule. This is done based on
  data from the F1 API. It serves as a fallback in case of team (name) changes or when plotting
  data of a future season where FastF1 has no built-in constants (yet).
  Note that auto-generated team name constants may be imperfect. When auto-generated,
  all color schemes will follow the 'official' color scheme. (#848)

- Preliminary team name and color constants for 2026 have been added. Further changes may be
  made at the beginning of the season to better capture the teams identities and branding and
  to make the color palette more distinguishable. (#848)


Bug Fixes
^^^^^^^^^

- Prevent support race drivers from being included in the driver list and result data. This
  previously occurred in some edge cases due to bad source data. (#836)

- ``RateLimitExceededError`` is now raised as intended an no longer captured and hidden by
  internal error handling (#748, #842).


Deprecations
^^^^^^^^^^^^

- Importing ``ErgastError``, ``ErgastJsonError`` and ``ErgastInvalidRequestError`` from
  ``fastf1.ergast.interface`` is deprecate. Import from ``fastf1.exceptions`` instead.

- Importing ``NoLapDataError``, ``DataNotLoadedError`` and ``InvalidSessionError`` from
  ``fastf1.core`` is deprecate. Import from ``fastf1.exceptions`` instead.

- Importing ``RateLimitExceededError`` from ``fastf1`` is deprecated. Import from
  ``fastf1.exceptions`` instead.


Note: Deprecated API is removed two minor releases after its deprecation.
