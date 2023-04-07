import datetime

import pandas as pd
import pytest

import fastf1.core
import fastf1.events


@pytest.mark.parametrize("gp", ['Bahrain', 'Bharain', 'Sakhir', 1])
@pytest.mark.parametrize("identifier", ['Q', 4, 'Qualifying'])
def test_get_session(gp, identifier):
    session = fastf1.get_session(2021, gp, identifier)
    assert session.event['EventName'] == 'Bahrain Grand Prix'
    assert session.name == 'Qualifying'


@pytest.mark.parametrize("test_n, pass_1", [(0, False), (1, True), (2, False)])
@pytest.mark.parametrize(
    "session_n, pass_2",
    [(0, False), (1, True), (2, True), (3, True), (4, False)]
)
def test_get_testing_session(test_n, session_n, pass_1, pass_2):
    if pass_1 and pass_2:
        session = fastf1.get_testing_session(2022, test_n, session_n)
        assert isinstance(session, fastf1.core.Session)
        assert session.name == f"Practice {session_n}"
    else:
        with pytest.raises(ValueError):
            fastf1.get_testing_session(2022, test_n, session_n)


@pytest.mark.parametrize("dt", [datetime.datetime(year=2022, month=6, day=1)])
def test_get_events_remaining(dt):
    events = fastf1.get_events_remaining(dt)
    assert len(events) == 15


@pytest.mark.parametrize("dt",
                         [datetime.datetime(year=2022, month=12, day=31)])
def test_events_remaining_after_season(dt):
    events = fastf1.get_events_remaining(dt)
    assert len(events) == 0


@pytest.mark.parametrize("dt", [datetime.datetime(year=2022, month=1, day=1)])
def test_events_remaining_before_season(dt):
    events = fastf1.get_events_remaining(dt)
    assert len(events) == 23


@pytest.mark.parametrize("gp", ['Bahrain', 'Bharain', 'Sakhir', 1])
def test_get_event(gp):
    event = fastf1.get_event(2021, gp)
    assert event.EventName == 'Bahrain Grand Prix'


def test_get_event_round_zero():
    with pytest.raises(ValueError, match="testing event by round number"):
        fastf1.get_event(2021, 0)


def test_get_testing_event():
    # 0 is not a valid number for a testing event
    with pytest.raises(ValueError):
        fastf1.get_testing_event(2022, 0)

    session = fastf1.get_testing_event(2022, 1)
    assert isinstance(session, fastf1.events.Event)

    # only one testing event in 2021
    with pytest.raises(ValueError):
        fastf1.get_testing_event(2021, 2)


def test_event_schedule_partial_data_init():
    schedule = fastf1.events.EventSchedule(
        {'EventName': ['A', 'B', 'C'], 'Session1Date': [None, None, None],
         'Session1DateUTC': [None, None, None]}
    )
    assert schedule.dtypes['EventName'] == 'object'
    assert schedule.dtypes['Session1Date'] == 'object'
    assert schedule.dtypes['Session1DateUTC'] == '<M8[ns]'


def test_event_schedule_constructor_sliced():
    schedule = fastf1.events.EventSchedule({'EventName': ['A', 'B', 'C']},
                                           year=2020)
    event = schedule.iloc[0]
    assert isinstance(event, fastf1.events.Event)
    assert event.year == 2020


def test_event_schedule_is_testing():
    schedule = fastf1.events.EventSchedule(
        {'EventFormat': ['conventional', 'testing']}
    )
    assert (schedule.is_testing() == [False, True]).all()


def test_event_schedule_get_event_by_round_number():
    schedule = fastf1.events.EventSchedule(
        {'EventName': ['T1', 'A', 'B', 'C', 'D'],
         'RoundNumber': [0, 1, 2, 3, 4]}
    )
    assert schedule.get_event_by_round(2).EventName == 'B'

    with pytest.raises(ValueError, match="testing event by round number"):
        schedule.get_event_by_round(0)

    with pytest.raises(ValueError, match="Invalid round"):
        schedule.get_event_by_round(10)


def test_event_schedule_get_by_name():
    schedule = fastf1.events.EventSchedule(
        {
            'EventName': [
                'testA',
                'TESTB',
                'test_test'
            ]
        }
    )

    assert schedule.get_event_by_name('testA').EventName == 'testA'
    assert schedule.get_event_by_name('TESTA').EventName == 'testA'
    assert schedule.get_event_by_name('testb').EventName == 'TESTB'
    assert schedule.get_event_by_name('test-test').EventName == 'test_test'


def test_event_is_testing():
    assert fastf1.get_testing_event(2022, 1).is_testing()
    assert not fastf1.get_event(2022, 1).is_testing()


def test_event_get_session_name():
    event = fastf1.get_event(2021, 1)
    assert event.get_session_name(3) == 'Practice 3'
    assert event.get_session_name('Q') == 'Qualifying'
    assert event.get_session_name('praCtice 1') == 'Practice 1'

    # sprint qualifying name peculiarities
    event = fastf1.get_event(2021, 14)
    assert event.year == 2021
    assert event.get_session_name('SQ') == 'Sprint Qualifying'
    assert event.get_session_name('S') == 'Sprint Qualifying'
    assert event.get_session_name('Sprint') == 'Sprint Qualifying'
    assert event.get_session_name('Sprint Qualifying') == 'Sprint Qualifying'

    event = fastf1.get_event(2022, 4)
    assert event.year == 2022
    assert event.get_session_name('SQ') == 'Sprint'
    assert event.get_session_name('S') == 'Sprint'
    assert event.get_session_name('Sprint') == 'Sprint'
    assert event.get_session_name('Sprint Qualifying') == 'Sprint'


def test_event_get_session_date():
    event = fastf1.get_event(2021, 1)

    sd = event.get_session_date('Q', utc=True)
    assert sd == event.Session4DateUTC
    assert isinstance(sd, pd.Timestamp)

    sd = event.get_session_date('Q', utc=False)
    assert sd == event.Session4Date
    assert isinstance(sd, pd.Timestamp)


@pytest.mark.parametrize(
    "meth_name,args,expected_name",
    [
        ['get_session', ['qualifying'], 'Qualifying'],
        ['get_session', ['R'], 'Race'],
        ['get_session', [1], 'Practice 1'],
        ['get_race', [], 'Race'],
        ['get_qualifying', [], 'Qualifying'],
        ['get_sprint', [], 'Sprint Qualifying'],
        ['get_practice', [1], 'Practice 1'],
        ['get_practice', [2], 'Practice 2'],
    ]
)
def test_event_get_session(meth_name, args, expected_name):
    event = fastf1.get_event(2021, 14)
    session = getattr(event, meth_name)(*args)
    assert session.name == expected_name


def test_event_get_nonexistent_session():
    with pytest.raises(ValueError, match="does not exist"):
        fastf1.get_session(2020, 13, 'FP2')


def test_event_get_nonexistent_session_date():
    event = fastf1.get_event(2020, 13)
    with pytest.raises(ValueError, match="does not exist"):
        event.get_session_date('FP2')
