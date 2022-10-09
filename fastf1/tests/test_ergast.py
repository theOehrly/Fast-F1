import pytest

import datetime

from fastf1.ergast.structure import \
    date_from_ergast, \
    time_from_ergast, \
    timedelta_from_ergast


def test_date_from_ergast():
    assert date_from_ergast('2022-10-25') == datetime.datetime(2022, 10, 25)


@pytest.mark.parametrize(
    "time_string, expected",
    (
            ("10:30:25.123456+00:00",
             datetime.time(hour=10, minute=30, second=25, microsecond=123456,
                           tzinfo=datetime.timezone.utc)),
            ("10:30:25.123456Z",
             datetime.time(hour=10, minute=30, second=25, microsecond=123456,
                           tzinfo=datetime.timezone.utc)),
            ("10:30:25.123456",
             datetime.time(hour=10, minute=30, second=25, microsecond=123456)),


            ("10:30:25.12+00:00",
             datetime.time(hour=10, minute=30, second=25, microsecond=120000,
                           tzinfo=datetime.timezone.utc)),
            ("10:30:25.12Z",
             datetime.time(hour=10, minute=30, second=25, microsecond=120000,
                           tzinfo=datetime.timezone.utc)),
            ("10:30:25.12",
             datetime.time(hour=10, minute=30, second=25, microsecond=120000)),


            ("10:30:25+00:00",
             datetime.time(hour=10, minute=30, second=25,
                           tzinfo=datetime.timezone.utc)),
            ("10:30:25Z",
             datetime.time(hour=10, minute=30, second=25,
                           tzinfo=datetime.timezone.utc)),
            ("10:30:25",
             datetime.time(hour=10, minute=30, second=25)),


            ("1:30:25+00:00",
             datetime.time(hour=1, minute=30, second=25,
                           tzinfo=datetime.timezone.utc)),
            ("1:30:25Z",
             datetime.time(hour=1, minute=30, second=25,
                           tzinfo=datetime.timezone.utc)),
            ("1:30:25",
             datetime.time(hour=1, minute=30, second=25)),

            ("10:30:25+05:30",
             datetime.time(hour=10, minute=30, second=25,
                           tzinfo=datetime.timezone(
                               datetime.timedelta(hours=5, minutes=30)
                           ))),
            ("10:30:25-05:30",
             datetime.time(hour=10, minute=30, second=25,
                           tzinfo=datetime.timezone(
                               datetime.timedelta(hours=-5, minutes=-30)
                           ))),
            ("10:30:25+00:00",
             datetime.time(hour=10, minute=30, second=25,
                           tzinfo=datetime.timezone.utc)),
            ("10:30:25Z",
             datetime.time(hour=10, minute=30, second=25,
                           tzinfo=datetime.timezone.utc)),
            ("10:30:25",
             datetime.time(hour=10, minute=30, second=25)),


            ("5:25.12+00:00",
             datetime.time(minute=5, second=25, microsecond=120000,
                           tzinfo=datetime.timezone.utc)),
            ("5:25.12Z",
             datetime.time(minute=5, second=25, microsecond=120000,
                           tzinfo=datetime.timezone.utc)),
            ("5:25.12",
             datetime.time(minute=5, second=25, microsecond=120000)),


            ("5.12+00:00",
             datetime.time(second=5, microsecond=120000,
                           tzinfo=datetime.timezone.utc)),
            ("5.12Z",
             datetime.time(second=5, microsecond=120000,
                           tzinfo=datetime.timezone.utc)),
            ("5.12",
             datetime.time(second=5, microsecond=120000)),
    )
)
def test_time_from_ergast(time_string, expected):
    assert time_from_ergast(time_string) == expected


@pytest.mark.parametrize(
    "time_string, expected",
    (
            ("10:30:25.123456",
             datetime.timedelta(hours=10, minutes=30, seconds=25,
                                microseconds=123456)),

            ("+10:30:25.123456",
             datetime.timedelta(hours=10, minutes=30, seconds=25,
                                microseconds=123456)),

            ("-10:30:25.123456",
             -datetime.timedelta(hours=10, minutes=30, seconds=25,
                                 microseconds=123456)),

            ("10:30:25.12",
             datetime.timedelta(hours=10, minutes=30, seconds=25,
                                microseconds=120000)),

            ("10:30:25",
             datetime.timedelta(hours=10, minutes=30, seconds=25)),

            ("1:30:25",
             datetime.timedelta(hours=1, minutes=30, seconds=25)),

            ("10:30:25",
             datetime.timedelta(hours=10, minutes=30, seconds=25)),

            ("5:25.12",
             datetime.timedelta(minutes=5, seconds=25, microseconds=120000)),

            ("5.12",
             datetime.timedelta(seconds=5, microseconds=120000)),
    )
)
def test_timedelta_from_ergast(time_string, expected):
    assert timedelta_from_ergast(time_string) == expected
