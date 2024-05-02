import datetime

import pandas as pd
import pytest

import fastf1.core
import fastf1.events


@pytest.mark.parametrize('backend', ['fastf1', 'f1timing', 'ergast'])
@pytest.mark.parametrize("gp", ['Bahrain', 'Bharain', 'Sakhir', 1])
@pytest.mark.parametrize("identifier", ['Q', 4, 'Qualifying'])
def test_get_session(backend, gp, identifier):
    session = fastf1.get_session(2021, gp, identifier, backend=backend)
    assert session.event['EventName'] == 'Bahrain Grand Prix'
    assert session.name == 'Qualifying'


@pytest.mark.parametrize("test_n, pass_1", [(0, False), (1, True), (2, False)])
@pytest.mark.parametrize(
    "session_n, pass_2",
    [(0, False), (1, True), (2, True), (3, True), (4, False)]
)
def test_get_testing_session(test_n, session_n, pass_1, pass_2):
    if pass_1 and pass_2:
        session = fastf1.get_testing_session(2021, test_n, session_n)
        assert isinstance(session, fastf1.core.Session)
        assert session.name == f"Practice {session_n}"
    else:
        with pytest.raises(ValueError):
            fastf1.get_testing_session(2021, test_n, session_n)


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
    assert len(events) == 24


@pytest.mark.parametrize('backend', ['fastf1', 'f1timing', 'ergast'])
@pytest.mark.parametrize("gp", ['Bahrain', 'Bharain', 'Sakhir', 1])
def test_get_event(backend, gp):
    event = fastf1.get_event(2021, gp, backend=backend)
    assert event.EventName == 'Bahrain Grand Prix'


def test_get_event_round_zero():
    with pytest.raises(ValueError, match="testing event by round number"):
        fastf1.get_event(2021, 0)


def test_get_testing_event():
    # 0 is not a valid number for a testing event
    with pytest.raises(ValueError):
        fastf1.get_testing_event(2021, 0)

    session = fastf1.get_testing_event(2021, 1)
    assert isinstance(session, fastf1.events.Event)

    # only one testing event in 2021
    with pytest.raises(ValueError):
        fastf1.get_testing_event(2021, 2)


def test_event_schedule_partial_data_init():
    schedule = fastf1.events.EventSchedule(
        {'EventName': ['A', 'B', 'C'], 'Session1Date': [None, None, None],
         'Session1DateUtc': [None, None, None]}
    )
    assert schedule.dtypes['EventName'] == 'object'
    assert schedule.dtypes['Session1Date'] == 'object'
    assert schedule.dtypes['Session1DateUtc'] == '<M8[ns]'


def test_event_schedule_constructor_sliced():
    schedule = fastf1.events.EventSchedule({'EventName': ['A', 'B', 'C']},
                                           year=2020)
    event = schedule.iloc[0]
    assert isinstance(event, fastf1.events.Event)
    assert event.year == 2020


def test_event_schedule_is_testing():
    schedule = fastf1.events.EventSchedule({'EventFormat': [
        'conventional', 'sprint', 'sprint_shootout', 'testing'
    ]})

    assert (schedule.is_testing() == [False, False, False, True]).all()


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


def test_event_fuzzy_search():
    # highest overlap case
    schedule = fastf1.get_event_schedule(1979)
    assert schedule.get_event_by_name(
        "United States").EventName == "United States Grand Prix"
    assert schedule.get_event_by_name(
        "United States Grand Prix").EventName == "United States Grand Prix"
    assert schedule.get_event_by_name(
        "United States West").EventName == "United States Grand Prix West"
    assert schedule.get_event_by_name(
        "United States West Grand Prix").EventName == "United States Grand Prix West"
    assert schedule.get_event_by_name(
        "US West").EventName == "United States Grand Prix West"

    # Multiple races are held at the same venue during the 2020 season
    schedule = fastf1.get_event_schedule(2020)
    # Prefer Austrian GP over Styrian GP
    assert schedule.get_event_by_name(
        "Austria").EventName == "Austrian Grand Prix"
    # Prefer Bahrain GP over Sakhir GP
    assert schedule.get_event_by_name(
        "Bahrain").EventName == "Bahrain Grand Prix"

    # tests for common inputs
    schedule = fastf1.get_event_schedule(2024)
    assert schedule.get_event_by_name(
        "Saudi").EventName == "Saudi Arabian Grand Prix"
    assert schedule.get_event_by_name(
        "Saudi GP").EventName == "Saudi Arabian Grand Prix"
    assert schedule.get_event_by_name(
        "Saudi Grand Prix").EventName == "Saudi Arabian Grand Prix"
    assert schedule.get_event_by_name(
        "Jeddah").EventName == "Saudi Arabian Grand Prix"
    assert schedule.get_event_by_name(
        "Saudi Arabia").EventName == "Saudi Arabian Grand Prix"

    # tests agaisnt colloquialisms
    assert schedule.get_event_by_name(
        "Imola").EventName == "Emilia Romagna Grand Prix"
    assert schedule.get_event_by_name(
        "USGP").EventName == "United States Grand Prix"
    assert schedule.get_event_by_name(
        "US GP").EventName == "United States Grand Prix"
    assert schedule.get_event_by_name(
        "Mexican GP").EventName == "Mexico City Grand Prix"
    assert schedule.get_event_by_name(
        "Brazilian GP").EventName == "São Paulo Grand Prix"


@pytest.mark.parametrize(
    'backend, no_testing_support',
    [('fastf1', False), ('f1timing', False), ('ergast', True)],
)
def test_event_is_testing(backend, no_testing_support):
    if no_testing_support:
        with pytest.raises(ValueError):
            fastf1.get_testing_event(2022, 1, backend=backend)
    else:
        assert fastf1.get_testing_event(2022, 1, backend=backend).is_testing()
    assert not fastf1.get_event(2022, 1, backend=backend).is_testing()


@pytest.mark.parametrize('backend', ['fastf1', 'f1timing', 'ergast'])
def test_event_get_session_name(backend):
    # conventional event before sprint era
    event = fastf1.get_event(2019, 1, backend=backend)
    assert event.EventFormat == 'conventional'
    assert event.get_session_name(3) == 'Practice 3'
    assert event.get_session_name('Q') == 'Qualifying'
    assert event.get_session_name('praCtice 1') == 'Practice 1'

    # conventional event from sprint era
    event = fastf1.get_event(2021, 1, backend=backend)
    assert event.EventFormat == 'conventional'
    assert event.get_session_name(3) == 'Practice 3'
    assert event.get_session_name('Q') == 'Qualifying'
    assert event.get_session_name('praCtice 1') == 'Practice 1'

    # sprint qualifying name peculiarities
    event = fastf1.get_event(2021, 14, backend=backend)
    assert event.year == 2021
    assert event.EventFormat == 'sprint'
    assert event.get_session_name('SQ') == 'Sprint'
    assert event.get_session_name('S') == 'Sprint'
    assert event.get_session_name('Sprint') == 'Sprint'
    assert event.get_session_name('Sprint Qualifying') == 'Sprint'

    event = fastf1.get_event(2022, 4, backend=backend)
    assert event.year == 2022
    assert event.EventFormat == 'sprint'
    assert event.get_session_name('SQ') == 'Sprint'
    assert event.get_session_name('S') == 'Sprint'
    assert event.get_session_name('Sprint') == 'Sprint'
    assert event.get_session_name('Sprint Qualifying') == 'Sprint'

    # Sprint Shootout format introduced for 2023
    event = fastf1.get_event(2023, 4, backend=backend)
    assert event.year == 2023
    assert event.EventFormat == 'sprint_shootout'
    assert event.get_session_name('SS') == 'Sprint Shootout'
    assert event.get_session_name('S') == 'Sprint'
    assert event.get_session_name('Sprint Shootout') == 'Sprint Shootout'
    assert event.get_session_name('Sprint') == 'Sprint'

    # Sprint Qualifying format introduced for 2024
    if ((backend == 'f1timing')
            and (datetime.datetime.now() < datetime.datetime(2024, 4, 21))):
        # disables this test until the data should be available
        # TODO: remove early exit at any time after 2024/04/21
        return
    event = fastf1.get_event(2024, 5, backend=backend)
    assert event.year == 2024
    assert event.EventFormat == 'sprint_qualifying'
    assert event.get_session_name('SQ') == 'Sprint Qualifying'
    assert event.get_session_name('S') == 'Sprint'
    assert event.get_session_name('Sprint Qualifying') == 'Sprint Qualifying'
    assert event.get_session_name('Sprint') == 'Sprint'


@pytest.mark.parametrize(
    'backend, tz_support',
    [('fastf1', True), ('f1timing', True), ('ergast', False)]
)
def test_event_get_session_date(backend, tz_support):
    event = fastf1.get_event(2021, 1, backend=backend)

    sd = event.get_session_date('Q', utc=True)
    assert sd == event.Session4DateUtc
    assert isinstance(sd, pd.Timestamp)
    if tz_support:
        assert sd.tz is None  # utc timestamp is timezone-naive

    if tz_support:
        sd2 = event.get_session_date('Q', utc=False)
        assert sd2 == event.Session4Date
        assert isinstance(sd2, pd.Timestamp)
        assert sd2.tz is not None
    else:
        with pytest.raises(ValueError, match='Local timestamp'):
            event.get_session_date('Q', utc=False)


@pytest.mark.parametrize(
    "event_year,event_round,meth_name,args,expected_name",
    [
        [2021, 14, 'get_session', ['qualifying'], 'Qualifying'],
        [2021, 14, 'get_session', ['R'], 'Race'],
        [2021, 14, 'get_session', [1], 'Practice 1'],
        [2021, 14, 'get_session', ['sprint'], 'Sprint'],
        [2021, 14, 'get_race', [], 'Race'],
        [2021, 14, 'get_qualifying', [], 'Qualifying'],
        [2021, 14, 'get_sprint', [], 'Sprint'],
        [2021, 14, 'get_practice', [1], 'Practice 1'],
        [2021, 14, 'get_practice', [2], 'Practice 2'],
        [2023, 4, 'get_session', ['sprint shootout'], 'Sprint Shootout'],
        [2023, 4, 'get_session', ['ss'], 'Sprint Shootout'],
        [2023, 4, 'get_sprint_shootout', [], 'Sprint Shootout'],
    ]
)
def test_event_get_session(
        event_year, event_round, meth_name, args, expected_name):
    event = fastf1.get_event(event_year, event_round)
    session = getattr(event, meth_name)(*args)
    assert session.name == expected_name


def test_event_get_nonexistent_session():
    with pytest.raises(ValueError, match="does not exist"):
        fastf1.get_session(2020, 13, 'FP2')


def test_event_get_nonexistent_session_date():
    event = fastf1.get_event(2020, 13)
    with pytest.raises(ValueError, match="does not exist"):
        event.get_session_date('FP2')


def test_events_constructors():
    frame = fastf1.events.EventSchedule({'RoundNumber': [1, 2, 3],
                                         'Country': ['a', 'b', 'c']})

    # test slicing to frame
    assert isinstance(frame.iloc[1:], fastf1.events.EventSchedule)

    # test horizontal slicing
    assert isinstance(frame.iloc[0], fastf1.events.Event)
    assert isinstance(frame.iloc[0], pd.Series)

    # test vertical slicing
    assert not isinstance(frame.loc[:, 'Country'], fastf1.events.Event)
    assert isinstance(frame.loc[:, 'Country'], pd.Series)

    # test base class view
    assert isinstance(frame.base_class_view, pd.DataFrame)
    assert not isinstance(frame.base_class_view, fastf1.events.EventSchedule)
