import datetime

import pytest

from fastf1.utils import (
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
        with pytest.warns(DeprecationWarning,                                                                                                                                                                                            
                            match="fastf1.utils.to_timedelta"): 
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
        with pytest.warns(DeprecationWarning,
                            match="fastf1.utils.to_datetime"):
            assert to_datetime(ts) == expected


def test_recursive_dict_get_deprecated():
    from fastf1.utils import recursive_dict_get
    data = {'a': {'b': {'c': 42}}}
    with pytest.warns(DeprecationWarning):
        assert recursive_dict_get(data, 'a', 'b', 'c') == 42
    with pytest.warns(DeprecationWarning):
        assert recursive_dict_get(data, 'a', 'missing') == {}
    with pytest.warns(DeprecationWarning):
        assert recursive_dict_get(data, 'a', 'missing',
                                  default_none=True) is None