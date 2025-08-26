.. _logging:

Logging
=======

.. currentmodule:: fastf1


Configure Logging Verbosity
---------------------------

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


Advanced Logging API
--------------------

.. _advanced-logging:

This section is usually only relevant for developers and contains information
that is useful for debugging and for implementing logging in FastF1 internal
code.

FastF1 uses loggers for each submodule. All loggers are child loggers of
FastF1's base logger. The log level is usually configured equally for all parts
of FastF1. The :class:`~fastf1.logger.LoggingManager` or the direct access
functions should commonly be used for this.

Note to developers: some parts of FastF1's data loading are wrapped in generic
catch-all error handling to prevent errors in individual data loading tasks to
make FastF1 completely unusable. Instead, unhandled exceptions will be caught,
short error message is logged in level INFO, the full traceback is logged on
level DEBUG and execution will continue as good as possible. This system can
make debugging more difficult because errors are not raised. To circumvent
this, there are two possible ways to disable the catch-all error handling for
data loading:

- explicitly set :attr:`fastf1.logger.LoggingManager.debug` to `True`
- set the environment variable `FASTF1_DEBUG=1`


Logging Manager
...............

.. autoclass:: fastf1.logger.LoggingManager
    :members:


Functions for direct access
...........................

.. automethod:: fastf1.logger.set_log_level
.. automethod:: fastf1.logger.get_logger
.. automethod:: fastf1.logger.soft_exceptions

.. automodule:: fastf1.logger
    :show-inheritance:
