What's new in v3.7.0
--------------------

(released 28/11/2025)


New Features
^^^^^^^^^^^^

- Python 3.14 is now officially supported.

- Major overhaul of the documentation with changes to the overall structure and design. Support for switching between
  multiple documentation versions is available going forward from now.

- The livetiming client now uses a new endpoint and protocol. This follows changes by Formula 1, who have
  gradually phased out the old endpoints.

- Support for authentication with an F1TV Access/Pro/Premium subscription has been added. Authentication is only
  required when using the new live timing client, since the new endpoints no longer allow unauthenticated access. This
  change has no effect on the majority of users who only load data after a session has ended.


Bug Fixes
^^^^^^^^^

- Improved handling of unexpected data types in the Jolpica/Ergast API client to prevent crashes caused by
  incorrect or unexpected external data. (#814)

- Fixed a bug that caused the "auto-cast" feature of the Ergast API client to not cast values of any objects
  that were contained inside a JSON array. This bug was only encountered when using raw responses instead of
  DataFrames. (#797)

- Various bugs related to usage of the live timing client and loading of created recordings have been fixed.
