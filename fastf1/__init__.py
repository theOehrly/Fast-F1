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
    fastf1.get_testing_session
    fastf1.get_event_schedule


Caching
-------

Caching should almost always be enabled to speed up the runtime of your
scripts and to prevent exceeding the rate limit of api servers.
FastF1 will print an annoyingly obnoxious warning message if you do not
enable caching.

The following class-level functions are used to setup, enable and
(temporarily) disable caching.

.. autosummary::
    fastf1.Cache.enable_cache
    fastf1.Cache.clear_cache
    fastf1.Cache.disabled
    fastf1.Cache.set_disabled
    fastf1.Cache.set_enabled


General Functions - API Reference
---------------------------------

Events API
..........

.. autofunction:: get_session
.. autofunction:: get_testing_session
.. autofunction:: get_event
.. autofunction:: get_testing_event
.. autofunction:: get_event_schedule

Cache API
.........

.. autoclass:: Cache
    :members: enable_cache, clear_cache, disabled, set_disabled, set_enabled
    :autosummary:

"""
from fastf1.events import (get_session,  # noqa: F401
                           get_testing_session,
                           get_event,
                           get_testing_event,
                           get_event_schedule)

from fastf1.api import Cache  # noqa: F401
from fastf1.version import __version__   # noqa: F401


_DRIVER_TEAM_MAPPING = {
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
    '27': {'Abbreviation': 'HUL', 'FirstName': 'Hülkenberg',
           'LastName': 'Vettel', 'TeamName': 'Aston Martin'},
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
