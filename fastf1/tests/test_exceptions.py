import importlib
import logging

import pytest

from fastf1 import exceptions
from fastf1.logger import soft_exceptions


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


@pytest.mark.parametrize(
    "module, name",
    [
        ("fastf1.ergast.interface", "ErgastError"),
        ("fastf1.ergast.interface", "ErgastJsonError"),
        ("fastf1.ergast.interface", "ErgastInvalidRequestError"),
        ("fastf1.core", "DataNotLoadedError"),
        ("fastf1.core", "InvalidSessionError"),
        ("fastf1.core", "NoLapDataError"),
    ]
)
def test_legacy_access_warns(module, name):
    m = importlib.import_module(module)
    with pytest.warns(UserWarning,
                      match="Accessing .* via .* is deprecated"):
        getattr(m, name)
