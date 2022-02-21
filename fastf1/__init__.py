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
