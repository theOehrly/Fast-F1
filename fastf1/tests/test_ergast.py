import logging

import pandas as pd
import pytest

import datetime

from fastf1.ergast.interface import \
    Ergast, \
    ErgastResponseMixin, \
    ErgastResultFrame, \
    ErgastResultSeries, \
    ErgastRawResponse

import fastf1.ergast.structure as API
from fastf1.ergast.structure import \
    date_from_ergast, \
    time_from_ergast, \
    timedelta_from_ergast


# ############### test structure.py #################################

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
    "time_string",
    (
        "huh?",
        "10:30:75"
    )
)
def test_time_from_ergast_errors(time_string, caplog):
    caplog.set_level(logging.DEBUG)
    assert time_from_ergast(time_string) is None
    assert "Failed to parse" in caplog.text


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


@pytest.mark.parametrize(
    "time_string",
    (
        "nope, not a timestamp",
        "10:30:75.123456",
    )
)
def test_timedelta_from_ergast_error(time_string, caplog):
    caplog.set_level(logging.DEBUG)
    assert timedelta_from_ergast(time_string) is None
    assert "Failed to parse" in caplog.text


@pytest.mark.parametrize(
    "data, cast, rename, expected",
    (
        ({'Value1': '10', 'Value2': '20'}, False, False,
         {'Value1': '10', 'Value2': '20'}),
        ({'Value1': '10', 'Value2': '20'}, False, True,
         {'value_1': '10', 'value_2': '20'}),
        ({'Value1': '10', 'Value2': '20'}, True, False,
         {'Value1': '10', 'Value2': 20.0}),
        ({'Value1': '10', 'Value2': '20'}, True, True,
         {'value_1': '10', 'value_2': 20.0}),
        ({'unknown': '0x05', 'Value2': '20'}, True, True,
         {'value_2': 20.0}),
    )

)
def test_flatten_by_rename(data, cast, rename, expected):
    test_category = {
        'name': 'Test',
        'type': dict,
        'method': API._flatten_by_rename,
        'map': {'Value1': {'name': 'value_1', 'type': str},
                'Value2': {'name': 'value_2', 'type': float}},
        'sub': [],
        'finalize': None
    }

    flat = {}
    API._flatten_by_rename(data, test_category, flat, cast=cast, rename=rename)
    assert flat == expected


@pytest.mark.parametrize(
    "data, cast, rename, expected",
    (
        ([{'Value1': '10', 'Value2': '20'}, {'Value1': '11', 'Value2': '21'}],
         False, False,
         {'Value1': ['10', '11'], 'Value2': ['20', '21']}),

        ([{'Value1': '10', 'Value2': '20'}, {'Value1': '11', 'Value2': '21'}],
         False, True,
         {'value_1': ['10', '11'], 'value_2': ['20', '21']}),

        ([{'Value1': '10', 'Value2': '20'}, {'Value1': '11', 'Value2': '21'}],
         True, False,
         {'Value1': ['10', '11'], 'Value2': [20.0, 21.0]}),

        ([{'Value1': '10', 'Value2': '20'}, {'Value1': '11', 'Value2': '21'}],
         True, True,
         {'value_1': ['10', '11'], 'value_2': [20.0, 21.0]}),

        ([{'Value1': '10', 'unknown': 'a'}, {'Value1': '11', 'unknown': 'b'}],
         True, True,
         {'value_1': ['10', '11']}),
    )
)
def test_flatten_inline_list_of_dicts(data, cast, rename, expected):
    test_category = {
        'name': 'Test',
        'type': dict,
        'method': API._flatten_inline_list_of_dicts,
        'map': {'Value1': {'name': 'value_1', 'type': str},
                'Value2': {'name': 'value_2', 'type': float}},
        'sub': [],
        'finalize': None
    }

    flat = {}
    API._flatten_inline_list_of_dicts(
        data, test_category, flat, cast=cast, rename=rename
    )
    assert flat == expected


def test_lap_timings_flatten_by_rename():
    data = {"number": "1", "Timings": [
            {"driverId": "hamilton", "position": "1", "time": "1:42.678"},
            {"driverId": "alonso", "position": "2", "time": "1:43.223"}]}

    expected = {'number': ['1', '1'], 'driverId': ['hamilton', 'alonso'],
                'position': ['1', '2'], 'time': ["1:42.678", "1:43.223"]}

    test_category = API.Laps
    flat = {}
    API._lap_timings_flatten_by_rename(
        data, test_category, flat, cast=False, rename=False
    )
    assert flat == expected


@pytest.mark.parametrize(
    "data, expected",
    (
        ([{'value_1': [1, 2, 3], 'value_2': [11, 12, 13]}],
         {'value_1': [1, 2, 3], 'value_2': [11, 12, 13]}),

        ([{'value_1': [1, 2, 3], 'value_2': [11, 12, 13]},
          {'value_1': [4, 5, 6], 'value_2': [14, 15, 16]}],
         {'value_1': [1, 2, 3, 4, 5, 6], 'value_2': [11, 12, 13, 14, 15, 16]})
    )
)
def test_merge_dicts_of_lists(data, expected):
    assert API._merge_dicts_of_lists(data) == expected


# ############### test interface.py #################################

@pytest.mark.parametrize(
    "endpoint, selectors, expected",
    (
        # "normal" behaviour for most endpoints
        ['seasons', {}, "https://ergast.com/api/f1/seasons.json"],

        ['circuits', {'driver': 'alonso', 'constructor': 'alpine'},
         "https://ergast.com/api/f1/constructors/alpine/"
         "drivers/alonso/circuits.json"],

        # special case where endpoint name matches selector
        ['laps', {'season': 2022, 'round': 10},
         "https://ergast.com/api/f1/2022/10/laps.json"],

        ['laps', {'season': 2022, 'round': 10, 'lap_number': 1},
         "https://ergast.com/api/f1/2022/10/laps/1.json"],

        # endpoint/selector combination in other request
        ['pitstops', {'season': 2022, 'round': 10, 'lap_number': 1},
         "https://ergast.com/api/f1/2022/10/laps/1/pitstops.json"],

        # combined selector standings_position
        ['driverStandings', {'season': 2022, 'standings_position': 1},
         "https://ergast.com/api/f1/2022/driverStandings/1.json"],

        ['constructorStandings', {'season': 2022, 'standings_position': 3},
         "https://ergast.com/api/f1/2022/constructorStandings/3.json"]
    )
)
def test_ergast_build_url(endpoint: str, selectors: dict, expected: str):
    assert Ergast._build_url(endpoint, **selectors) == expected


def test_ergast_response_mixin():
    response_headers = {'xmlns': 'http://ergast.com/mrd/1.5', 'series': 'f1',
                        'url': 'http://ergast.com/api/f1/2022/results.json',
                        'limit': '3', 'offset': '0', 'total': '440'}
    query_filters = {'season': '2022'}

    query_metadata = {'endpoint': 'results', 'table': 'RaceTable',
                      'category': API.Races_RaceResults,
                      'subcategory': API.RaceResults,
                      'result_type': 'raw', 'auto_cast': False}

    selectors = {'season': 2022, 'round': None, 'circuit': None,
                 'constructor': None, 'driver': None, 'grid_position': None,
                 'fastest_rank': None, 'status': None}

    class ErgastTest(Ergast):
        test_build_args = {}

        @classmethod
        def _build_result(cls, **kwargs):
            cls.test_build_args = kwargs

    class ErgastResponseMixinTest(ErgastResponseMixin):
        @property
        def _ergast_constructor(self):
            return ErgastTest

    def get_response_mixin():
        return ErgastResponseMixinTest(response_headers=response_headers,
                                       query_filters=query_filters,
                                       metadata=query_metadata,
                                       selectors=selectors)

    erm = get_response_mixin()

    # test info about total/complete
    assert erm.total_results == 440
    assert not erm.is_complete

    # started at offset=0, therefore no previous page
    with pytest.raises(ValueError, match="No more data before"):
        erm.get_prev_result_page()

    # mock get next result page and verify that _build_result was called
    # correctly
    erm.get_next_result_page()

    # verify offset shift and equivalent limit
    assert ErgastTest.test_build_args['limit'] == 3
    assert ErgastTest.test_build_args['offset'] == 3

    # verify complete metadata and selectors
    for key, value in query_metadata.items():
        assert ErgastTest.test_build_args[key] == value
    for key, value in selectors.items():
        assert ErgastTest.test_build_args['selectors'][key] == value

    # #### modify inputs: limit > total
    response_headers['limit'] = 500
    erm = get_response_mixin()

    assert erm.total_results == 440
    assert erm.is_complete

    with pytest.raises(ValueError, match="No more data before"):
        erm.get_prev_result_page()

    with pytest.raises(ValueError, match="No more data after"):
        erm.get_next_result_page()

    # #### modify inputs: offset > 0, limits > total
    response_headers['limit'] = 3
    response_headers['offset'] = 438

    erm = get_response_mixin()

    assert erm.total_results == 440
    assert not erm.is_complete

    # started at offset=0, therefore no previous page
    with pytest.raises(ValueError, match="No more data after"):
        erm.get_next_result_page()

    # mock get next result page and verify that _build_result was called
    # correctly
    erm.get_prev_result_page()

    # verify offset shift and equivalent limit
    assert ErgastTest.test_build_args['limit'] == 3
    assert ErgastTest.test_build_args['offset'] == 435

    # verify complete metadata and selectors
    for key, value in query_metadata.items():
        assert ErgastTest.test_build_args[key] == value
    for key, value in selectors.items():
        assert ErgastTest.test_build_args['selectors'][key] == value


def test_ergast_result_frame_constructors():
    frame = ErgastResultFrame({'A': [1, 2, 3], 'B': [1, 2, 3]})

    # test slicing to frame
    assert isinstance(frame.iloc[1:], ErgastResultFrame)

    # test horizontal slicing
    assert isinstance(frame.iloc[0], ErgastResultSeries)
    assert isinstance(frame.iloc[0], pd.Series)

    # test vertical slicing
    assert not isinstance(frame.loc[:, 'A'], ErgastResultSeries)
    assert isinstance(frame.loc[:, 'A'], pd.Series)

    # test base class view
    assert isinstance(frame.base_class_view, pd.DataFrame)
    assert not isinstance(frame.base_class_view, ErgastResultFrame)


def test_ergast_result_frame_prepare_response():
    data = [{
        "circuitId": "albert_park",
        "url": "https://...",
        "circuitName": "Albert Park Grand Prix Circuit",
        "Location": {"lat": "-37.8497",
                     "long": "144.968",
                     "locality": "Melbourne",
                     "country": "Australia"}
    }, {
        "circuitId": "bahrain",
        "url": "https://...",
        "circuitName": "Bahrain International Circuit",
        "Location": {"lat": "26.0325",
                     "long": "50.5106",
                     "locality": "Sakhir",
                     "country": "Bahrain"}
    }]

    expected = [{
        "circuitId": "albert_park",
        "circuitUrl": "https://...",
        "circuitName": "Albert Park Grand Prix Circuit",
        "lat": -37.8497,
        "long": 144.968,
        "locality": "Melbourne",
        "country": "Australia"
    }, {
        "circuitId": "bahrain",
        "circuitUrl": "https://...",
        "circuitName": "Bahrain International Circuit",
        "lat": 26.0325,
        "long": 50.5106,
        "locality": "Sakhir",
        "country": "Bahrain"
    }]

    result = ErgastResultFrame._prepare_response(data, API.Circuits, cast=True)
    assert result == expected


def test_ergast_result_series_constructor():
    series = ErgastResultSeries(data=[1, 2, 3], index=['A', 'B', 'C'])
    assert isinstance(series[1:], ErgastResultSeries)


def test_ergast_raw_response():
    # test auto-casting in subcategories (i.e. verify proper recursion as well)
    data = [{
        "circuitId": "albert_park",
        "url": "https://...",
        "circuitName": "Albert Park Grand Prix Circuit",
        "Location": {"lat": "-37.8497",
                     "long": "144.968",
                     "locality": "Melbourne",
                     "country": "Australia"}
    }, {
        "circuitId": "bahrain",
        "url": "https://...",
        "circuitName": "Bahrain International Circuit",
        "Location": {"lat": "26.0325",
                     "long": "50.5106",
                     "locality": "Sakhir",
                     "country": "Bahrain"}
    }]

    expected = [{
        "circuitId": "albert_park",
        "url": "https://...",
        "circuitName": "Albert Park Grand Prix Circuit",
        "Location": {"lat": -37.8497,  # cast from str
                     "long": 144.968,
                     "locality": "Melbourne",
                     "country": "Australia"}
    }, {
        "circuitId": "bahrain",
        "url": "https://...",
        "circuitName": "Bahrain International Circuit",
        "Location": {"lat": 26.0325,
                     "long": 50.5106,
                     "locality": "Sakhir",
                     "country": "Bahrain"}
    }]

    result = ErgastRawResponse(query_result=data,
                               category=API.Circuits,
                               auto_cast=True,
                               # set invalid arguments for Mixin: not required
                               response_headers=None,
                               query_filters=None,
                               metadata=None,
                               selectors=None)
    assert result == expected


@pytest.mark.ergastapi
def test_ergast_api_endpoints_raw_and_defaults():
    result_1 = Ergast(auto_cast=False, result_type='raw', limit=3) \
        .get_seasons()

    result_2 = Ergast(auto_cast=True, result_type='pandas', limit=100) \
        .get_seasons(auto_cast=False, result_type='raw', limit=3)

    assert isinstance(result_1[0]['season'], str)  # no casting
    assert len(result_1) == 3  # limit is correct
    assert result_1 == result_2  # defaults and default override equivalent

    # now with auto-casting
    result_3 = Ergast(auto_cast=True, result_type='raw', limit=3) \
        .get_seasons()

    assert isinstance(result_3[0]['season'], int)  # cast year to int


@pytest.mark.ergastapi
def test_ergast_api_endpoints_simple_response():
    result = Ergast(auto_cast=True, result_type='pandas', limit=3) \
        .get_seasons()

    assert result.shape == (3, 2)  # correct dataframe shape
    assert 'season' in result.columns  # columns correct and renamed
    assert 'seasonUrl' in result.columns
    assert result['season'].dtype == 'int64'


@pytest.mark.ergastapi
def test_ergast_api_endpoints_multi_response():
    result = Ergast(auto_cast=True, result_type='pandas', limit=30) \
        .get_race_results(season=2020)

    assert result.description.shape == (2, 13)  # correct dataframe shape
    assert len(result.content) == 2  # content length == description rows

    assert result.content[0].shape[1] == 26  # correct dataframe shape
    assert 'fastestLapTime' in result.content[0].columns  # columns renamed
    assert result.content[0]['fastestLapTime'].dtype == '<m8[ns]'  # casting
