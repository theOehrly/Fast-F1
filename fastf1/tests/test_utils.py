import datetime

from fastf1.utils import (
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
    for ts, expected in cases:
        assert to_datetime(ts) == expected


def test_to_timedelta_passthrough():
    td = datetime.timedelta(hours=1, minutes=30, seconds=5)
    assert to_timedelta(td) is td


def test_to_timedelta_none_and_empty():
    assert to_timedelta(None) is None
    assert to_timedelta('') is None


def test_to_timedelta_invalid_string():
    assert to_timedelta('not-a-time') is None


def test_to_datetime_passthrough():
    dt = datetime.datetime(2021, 3, 28, 10, 0, 0)
    assert to_datetime(dt) is dt


def test_to_datetime_none_and_empty():
    assert to_datetime(None) is None
    assert to_datetime('') is None


def test_to_datetime_invalid_string():
    assert to_datetime('not-a-datetime') is None


def test_recursive_dict_get_basic():
    d = {'a': {'b': {'c': 42}}}
    assert recursive_dict_get(d, 'a', 'b', 'c') == 42


def test_recursive_dict_get_missing_key_returns_empty_dict():
    d = {'a': {'b': 1}}
    assert recursive_dict_get(d, 'a', 'x') == {}


def test_recursive_dict_get_missing_key_default_none():
    d = {'a': {'b': 1}}
    assert recursive_dict_get(d, 'a', 'x', default_none=True) is None


def test_recursive_dict_get_single_key():
    d = {'key': 'value'}
    assert recursive_dict_get(d, 'key') == 'value'


def test_recursive_dict_get_empty_dict():
    assert recursive_dict_get({}, 'a', 'b') == {}
    assert recursive_dict_get({}, 'a', default_none=True) is None
