"""Tests for the private :mod:`fastf1._utils` module.

These mirror the public tests in ``test_utils.py`` but target the private
implementation directly. Calling the private functions must not emit any
warnings (the public wrappers in :mod:`fastf1.utils` are responsible for the
``DeprecationWarning``).
"""
import datetime
import warnings

from fastf1._utils import (
    recursive_dict_get,
    to_datetime,
    to_timedelta
)


def test_to_timedelta():
    cases = [
        ('13:24:46.320215',
         datetime.timedelta(hours=13, minutes=24,
                            seconds=46, microseconds=320215)),
        ('13:24:46.32',
         datetime.timedelta(hours=13, minutes=24,
                            seconds=46, microseconds=320000)),
        ('13:24:46.',
         datetime.timedelta(hours=13, minutes=24,
                            seconds=46, microseconds=0)),
        ('13:24:46', datetime.timedelta(hours=13, minutes=24, seconds=46)),
        ('24:46', datetime.timedelta(minutes=24, seconds=46)),
        ('4:46', datetime.timedelta(minutes=4, seconds=46)),
        ('46', datetime.timedelta(seconds=46)),
        ('4:46.5264', datetime.timedelta(minutes=4, seconds=46,
                                         microseconds=526400)),
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for ts, expected in cases:
            assert to_timedelta(ts) == expected


def test_to_datetime():
    cases = [
        ('2020-12-13T13:27:15.320653Z',
         datetime.datetime(2020, 12, 13, 13, 27, 15, 320653)),
        ('2020-12-13T13:27:15.320000Z',
         datetime.datetime(2020, 12, 13, 13, 27, 15, 320000)),
        ('2020-12-13T13:27:15.320000',
         datetime.datetime(2020, 12, 13, 13, 27, 15, 320000)),
        ('2020-12-13T13:27:15.32Z',
         datetime.datetime(2020, 12, 13, 13, 27, 15, 320000)),
        ('2020-12-13T13:27:15',
         datetime.datetime(2020, 12, 13, 13, 27, 15, 0)),
        ('2020-12-13T13:27:15.',
         datetime.datetime(2020, 12, 13, 13, 27, 15, 0)),
        (datetime.datetime(2020, 12, 13, 13, 27, 15, 0),
         datetime.datetime(2020, 12, 13, 13, 27, 15, 0))
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        for ts, expected in cases:
            assert to_datetime(ts) == expected


def test_recursive_dict_get():
    data = {'a': {'b': {'c': 42}}}
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert recursive_dict_get(data, 'a', 'b', 'c') == 42
        assert recursive_dict_get(data, 'a', 'b') == {'c': 42}
        assert recursive_dict_get(data, 'a', 'missing') == {}
        assert recursive_dict_get(data, 'a', 'missing',
                                  default_none=True) is None
        assert recursive_dict_get(data, 'a', 'b', 'c',
                                  default_none=True) == 42