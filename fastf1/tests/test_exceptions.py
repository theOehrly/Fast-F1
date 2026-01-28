import importlib
import logging

import pytest

from fastf1 import exceptions
from fastf1.logger import soft_exceptions
from fastf1.testing import (
    capture_log,
    run_in_subprocess
)


# ensure legacy import and access to exceptions
# removal schedule for v3.10

def test_legacy_import_warns():
    with pytest.warns(UserWarning,
                      match="Accessing .* via .* is deprecated"):
        from fastf1.ergast.interface import ErgastError

    with pytest.warns(UserWarning,
                      match="Accessing .* via .* is deprecated"):
        from fastf1.ergast.interface import ErgastJsonError

    with pytest.warns(UserWarning,
                      match="Accessing .* via .* is deprecated"):
        from fastf1.ergast.interface import ErgastInvalidRequestError

    with pytest.warns(UserWarning,
                      match="Accessing .* via .* is deprecated"):
        from fastf1.core import DataNotLoadedError

    with pytest.warns(UserWarning,
                      match="Accessing .* via .* is deprecated"):
        from fastf1.core import InvalidSessionError

    with pytest.warns(UserWarning,
                      match="Accessing .* via .* is deprecated"):
        from fastf1.core import NoLapDataError

    with pytest.warns(UserWarning,
                      match="Accessing .* via .* is deprecated"):
        from fastf1 import RateLimitExceededError


@pytest.mark.parametrize(
    "module, name",
    [
        ("fastf1.ergast.interface", "ErgastError"),
        ("fastf1.ergast.interface", "ErgastJsonError"),
        ("fastf1.ergast.interface", "ErgastInvalidRequestError"),
        ("fastf1.core", "DataNotLoadedError"),
        ("fastf1.core", "InvalidSessionError"),
        ("fastf1.core", "NoLapDataError"),
        ("fastf1", "RateLimitExceededError"),
    ]
)
def test_legacy_access_warns(module, name):
    m = importlib.import_module(module)
    with pytest.warns(UserWarning,
                      match="Accessing .* via .* is deprecated"):
        getattr(m, name)


def test_soft_exceptions_catch_and_warn():
    run_in_subprocess(_test_soft_exceptions_catch_and_warn)


def _test_soft_exceptions_catch_and_warn():
    logger = logging.getLogger()

    @soft_exceptions("test_function", "error in test function", logger)
    def func():
        raise ValueError

    log_handle = capture_log()

    # call the function, the error must be caught by the decorator
    func()

    # test that the warning message was logged
    assert "error in test function" in log_handle.text


def test_critical_exceptions_raise_in_soft_exceptions():
    run_in_subprocess(_test_critical_exceptions_raise_in_soft_exceptions)


def _test_critical_exceptions_raise_in_soft_exceptions():
    class TestCriticalError(exceptions.FastF1CriticalError):
        pass

    logger = logging.getLogger()

    @soft_exceptions("test_function", "error in test function", logger)
    def func():
        raise TestCriticalError

    log_handle = capture_log()

    # the error must be raised despite the decorator
    with pytest.raises(TestCriticalError):
        func()

    # test that the warning message was NOT logged
    assert "error in test function" not in log_handle.text
