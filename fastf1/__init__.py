"""
.. _GeneralFunctions:

General Functions - :mod:`fastf1`
=================================

.. currentmodule:: fastf1


Accessing Events and Sessions
-----------------------------

When using FastF1, you usually start by loading an event or a
session. This can be done with one of the following functions:

.. autosummary::
    fastf1.get_session
    fastf1.get_testing_session
    fastf1.get_event
    fastf1.get_events_remaining
    fastf1.get_testing_session
    fastf1.get_event_schedule


.. _requests-and-caching:

Requests and Caching
--------------------

.. automodule::
    fastf1.req

.. currentmodule:: fastf1


General Functions - API Reference
---------------------------------

Event and Session API
.....................

.. autofunction:: get_session
.. autofunction:: get_testing_session
.. autofunction:: get_event
.. autofunction:: get_events_remaining
.. autofunction:: get_testing_event
.. autofunction:: get_event_schedule

Cache API
.........

.. autoclass:: Cache
    :members: enable_cache, clear_cache, disabled, set_disabled, set_enabled,
        offline_mode
    :autosummary:


.. autoclass:: RateLimitExceededError


Configure Logging Verbosity
...........................

All parts of FastF1 generally log at the log level 'INFO'.
The reason for this is that many data loading processes take multiple
seconds to complete. Logging is used to give progress information here as well
as for showing warnings and non-terminal errors.

The logging level for FastF1 can be easily customized::

    import fastf1

    fastf1.set_log_level('WARNING')

    # ... your code  here ... #

The available levels are (in order of increasing severity): DEBUG, INFO,
WARNING, ERROR and CRITICAL.

.. autofunction:: set_log_level

For more information see :ref:`logging`.

"""
from typing import Dict

from fastf1.events import (get_session,  # noqa: F401
                           get_testing_session,
                           get_event,
                           get_events_remaining,
                           get_testing_event,
                           get_event_schedule)

from fastf1.logger import set_log_level  # noqa: F401

from fastf1.req import Cache, RateLimitExceededError   # noqa: F401
from fastf1.version import __version__   # noqa: F401


_DRIVER_TEAM_MAPPING: Dict[str, Dict[str, str]] = {
    # only necessary when loading live timing data that does not include
    # the driver and team listing and no data is available on ergast yet
    '23': {'Abbreviation': 'ALB', 'FirstName': 'Alexander',
           'LastName': 'Albon', 'TeamName': 'Williams'},
    '14': {'Abbreviation': 'ALO', 'FirstName': 'Fernando',
           'LastName': 'Alonso', 'TeamName': 'Alpine F1 Team'},
    '77': {'Abbreviation': 'BOT', 'FirstName': 'Valtteri',
           'LastName': 'Bottas', 'TeamName': 'Alfa Romeo'},
    '10': {'Abbreviation': 'GAS', 'FirstName': 'Pierre',
           'LastName': 'Gasly', 'TeamName': 'AlphaTauri'},
    '44': {'Abbreviation': 'HAM', 'FirstName': 'Lewis',
           'LastName': 'Hamilton', 'TeamName': 'Mercedes'},
    '27': {'Abbreviation': 'HUL', 'FirstName': 'Nico',
           'LastName': 'Hülkenberg', 'TeamName': 'Aston Martin'},
    '6': {'Abbreviation': 'LAT', 'FirstName': 'Nicholas',
          'LastName': 'Latifi', 'TeamName': 'Williams'},
    '16': {'Abbreviation': 'LEC', 'FirstName': 'Charles',
           'LastName': 'Leclerc', 'TeamName': 'Ferrari'},
    '20': {'Abbreviation': 'MAG', 'FirstName': 'Kevin',
           'LastName': 'Magnussen', 'TeamName': 'Haas F1 Team'},
    '4': {'Abbreviation': 'NOR', 'FirstName': 'Lando',
          'LastName': 'Norris', 'TeamName': 'McLaren'},
    '31': {'Abbreviation': 'OCO', 'FirstName': 'Esteban',
           'LastName': 'Ocon', 'TeamName': 'Alpine F1 Team'},
    '11': {'Abbreviation': 'PER', 'FirstName': 'Sergio',
           'LastName': 'Pérez', 'TeamName': 'Red Bull'},
    '3': {'Abbreviation': 'RIC', 'FirstName': 'Daniel',
          'LastName': 'Ricciardo', 'TeamName': 'McLaren'},
    '63': {'Abbreviation': 'RUS', 'FirstName': 'George',
           'LastName': 'Russell', 'TeamName': 'Mercedes'},
    '55': {'Abbreviation': 'SAI', 'FirstName': 'Carlos',
           'LastName': 'Sainz', 'TeamName': 'Ferrari'},
    '47': {'Abbreviation': 'MSC', 'FirstName': 'Mick',
           'LastName': 'Schumacher', 'TeamName': 'Haas F1 Team'},
    '18': {'Abbreviation': 'STR', 'FirstName': 'Lance',
           'LastName': 'Stroll', 'TeamName': 'Aston Martin'},
    '22': {'Abbreviation': 'TSU', 'FirstName': 'Yuki',
           'LastName': 'Tsunoda', 'TeamName': 'AlphaTauri'},
    '1': {'Abbreviation': 'VER', 'FirstName': 'Max',
          'LastName': 'Verstappen', 'TeamName': 'Red Bull'},
    '5': {'Abbreviation': 'VET', 'FirstName': 'Sebastian',
          'LastName': 'Vettel', 'TeamName': 'Aston Martin'},
    '24': {'Abbreviation': 'ZHO', 'FirstName': 'Guanyu',
           'LastName': 'Zhou', 'TeamName': 'Alfa Romeo'}
}
