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
    :members:
        enable_cache,
        clear_cache,
        get_cache_info,
        disabled,
        set_disabled,
        set_enabled,
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
try:
    from . import _version
except ImportError:
    _version = None

__version__ = getattr(_version, 'version', '0.0+UNKNOWN')
__version_tuple__ = getattr(_version, 'version_tuple', (0, 0, '+UNKNOWN'))
if __version_tuple__:
    # create a short version containing only the public version
    __version_short__ = ".".join(str(digit) for digit in __version_tuple__
                                 if str(digit).isnumeric())
else:
    __version_short__ = __version__


from fastf1.events import get_session  # noqa: F401
from fastf1.events import (  # noqa: F401
    get_event,
    get_event_schedule,
    get_events_remaining,
    get_testing_event,
    get_testing_session
)
from fastf1.logger import set_log_level  # noqa: F401
from fastf1.req import (  # noqa: F401
    Cache,
    RateLimitExceededError
)
