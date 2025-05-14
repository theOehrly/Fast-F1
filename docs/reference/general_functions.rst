General Functions
==================

.. currentmodule:: fastf1

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