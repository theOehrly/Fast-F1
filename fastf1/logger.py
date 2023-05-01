"""
.. _logging:

Logging - :mod:`fastf1.logger`
==============================

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

"""

import functools
import logging
import warnings
import os

from typing import Union


class LoggingManager:
    """Interface for configuring logging in FastF1.

    All parts of FastF1 generally log at the log level 'INFO'.
    The reason for this is that many data loading processes take multiple
    seconds to complete. Logging is used to give progress information as well
    as for showing warnings and non-terminal errors.

    All submodule loggers in FastF1 are child loggers of the base logger.
    This class acts as an interface to set the log level for FastF1 and get
    child loggers.
    """
    _console_formatter = logging.Formatter(
        "{module: <8} {levelname: >10} \t{message}", style='{'
    )

    _console_handler = logging.StreamHandler()
    _console_handler.setFormatter(_console_formatter)
    _console_handler.setLevel(logging.INFO)

    _root_logger = logging.getLogger('fastf1')
    _root_logger.setLevel(logging.DEBUG)
    _root_logger.addHandler(_console_handler)

    debug = False
    """Flag for enabling debug mode. This will disable catch-all error handling
    for data loading methods."""

    @classmethod
    def get_child(cls, name: str):
        """Return a logger with the given name that is child of the base
        logger.

        Args:
            name: name of the child logger
        """
        return cls._root_logger.getChild(name)

    @classmethod
    def set_level(cls, level: int):
        """Set the log level for FastF1.

        Args:
            level: log level, for example `logging.INFO`
        """
        cls._console_handler.setLevel(level)


if os.getenv('FASTF1_DEBUG') == '1':
    warnings.warn("Debug Mode enabled for Logger!", UserWarning)
    LoggingManager.debug = True
else:
    LoggingManager.debug = False


def get_logger(name: str):
    """Return a logger with the given name that is a child of FastF1's
    base logger.
    """
    return LoggingManager.get_child(name)


def set_log_level(level: Union[str, int]):
    """Set the log level for all parts of FastF1.

    When setting the log level for FastF1, only messages with this level or
    with a higher level will be shown.

    Args:
        level: Either a log level from the logging module (e.g. `logging.INFO`)
            or the level as a string (e.g. 'WARNING').
    """
    if isinstance(level, str):
        level = logging._nameToLevel.get(level.upper())
    LoggingManager.set_level(level)


def soft_exceptions(descr_name: str, msg: str, logger: logging.Logger):
    """Wrapper method for wrapping any function into catch-all error handling
    that can be disabled by setting :attr:`~fastf1.logger.LoggingManager.debug`
    to `True`.

    Args:
        descr_name: descriptive name for the type of data that should have
            been loaded by the wrapped function
        msg: Short message that is shown as error message to users
        logger: the logger that should be used to log errors
    """
    # This function is used to wrap individual data loading functions that are
    # called by `Session.load`. With the default configuration, this wrapper
    # will catch all unhandled exceptions in the wrapped function and log them.
    # The idea is that in case of an error, data loading will only fail
    # partially and FastF1 will not become completely unusable.
    # For development purposes the automatic error handling can be disabled
    # by explicitly setting `Logger.debug = True` or by setting the environment
    # variable `FASTF1_DEBUG=1`. In this case, all unhandled excpetions will
    # be raised.
    def __decorator(func):
        @functools.wraps(func)
        def __wrapped(*args, **kwargs):
            if not LoggingManager.debug:
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    logger.warning(msg)
                    logger.debug(f"Traceback for failure in {descr_name}",
                                 exc_info=exc)
            else:
                return func(*args, **kwargs)

        return __wrapped
    return __decorator
