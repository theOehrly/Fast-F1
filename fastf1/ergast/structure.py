import datetime
import re
from typing import Optional

from fastf1.logger import get_logger


logger = get_logger('ergast')


# ##############################################
# ### functions for date and time conversion ###

_time_string_matcher = re.compile(
    r'(\d{1,2}:)?(\d{1,2}:)?(\d{1,2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?'
)
# matches [hh:][mm:]ss[.micros][Z | +-hh:mm] timestring


def date_from_ergast(d_str) -> datetime.datetime:
    """Create a ``datetime.datetime`` object from a date stamp formatted
    like 'YYYY-MM-DD'."""
    return datetime.datetime.strptime(d_str, "%Y-%m-%d")


def time_from_ergast(t_str) -> Optional[datetime.time]:
    """Create a ``datetime.time`` object from a string that is formatted
    mostly like a timestamp according to ISO 8601. The implementation here only
    implements a subset of ISO 8601 to work around some missing functionality
    in ``datetime.time.fromisoformat`` in older versions of Python.

    Support timestamp format:
    [hh:][mm:]ss[.micros][Z/+-hh:mm]
    """
    # Examples for not supported strings on Python 3.8 in
    # ``datetime.time.fromisoformat``
    #   - 12:34.2 -> not accepted because only on microsecond decimal is given
    #   - 12:34Z  -> 'Z' is not accepted as an alias of '+00:00' (utc)

    res = _time_string_matcher.match(t_str)

    if res is None:
        logger.debug(f"Failed to parse timestamp '{t_str}' in Ergast"
                     f"response.")
        return None
    elif res[1] and res[2] and res[3]:
        hour, minute, second = int(res[1][:-1]), int(res[2][:-1]), int(res[3])
    elif res[1] and res[3]:
        hour, minute, second = 0, int(res[1][:-1]), int(res[3])
    else:
        hour, minute, second = 0, 0, int(res[3])

    if res[4]:
        digits = res[4][1:]
        microsecond = int(digits) * 10 ** (6 - len(digits))
    else:
        microsecond = 0

    if res[5] == 'Z':
        tzinfo = datetime.timezone.utc
    elif res[5]:
        tzinfo = datetime.datetime.strptime(res[5], "%z").tzinfo
    else:
        tzinfo = None

    try:
        return datetime.time(hour=hour, minute=minute, second=second,
                             microsecond=microsecond, tzinfo=tzinfo)
    except ValueError:
        logger.debug(f"Failed to parse timestamp '{t_str}' in Ergast"
                     f"response.")
        return None


def timedelta_from_ergast(t_str) -> Optional[datetime.timedelta]:
    """Create a ``datetime.timedelta`` object from a string that is formatted
    [+/-][hh:][mm:]ss[.micros], where all parts except for seconds are
    optional.
    """
    if t_str.startswith('-'):
        sign = -1
        t_str = t_str.strip('-')
    else:
        sign = 1
        t_str = t_str.strip('+')

    pseudo_time = time_from_ergast(t_str)
    if pseudo_time is not None:
        return sign * datetime.timedelta(hours=pseudo_time.hour,
                                         minutes=pseudo_time.minute,
                                         seconds=pseudo_time.second,
                                         microseconds=pseudo_time.microsecond)
    return None


# ########################################################
# ### functions for flattening of ergast response data ###


def _flatten_by_rename(nested: dict, category: dict, flat: dict, *,
                       cast: bool = True, rename: bool = True):
    """:meta private:
    Iterate over all values on the current level, rename them and
    add them to the flattened result dict. This is the default operation that
    is used for most Ergast responses.

    Values that are not defined by category will be skipped and are not added
    to the flattened result.

    This function operates inplace on 'nested' and 'flat'.
    """
    for name, mapping in category['map'].items():
        if name not in nested:
            continue

        value = nested[name]
        if cast:
            value = mapping['type'](value)

        if rename:
            flat[mapping['name']] = value
        else:
            flat[name] = value


def _flatten_inline_list_of_dicts(nested: list, category: dict, flat: dict, *,
                                  cast: bool = True, rename: bool = True):
    """:meta private:
    The current level is a single list of dictionaries, iterate over them and
    convert from a list of dictionaries::

        [
            {"constructorId": "mclaren", ... },
            {"constructorId": "mercedes", ... },
            ...
        ]

    to a dictionary of lists::

        {"constructorIds": ["mclaren", "mercedes", ...], ...}

    This structure can then be included in the flattened result.

    For comparison, "normal" flattening returns a dictionary of strings,
    numbers, ... but in this case, the most reasonable way is to create arrays
    for all the individual values instead.

    Multi-mapping (one entry in the nested data mapped to multiple entries
    in the flat data) is supported.
    """
    # iterate over all values on the current level , join and rename them and
    # add the resulting lists to the flattened result dict
    for name, mapping in category['map'].items():
        # generate list of values for each mapping
        joined = list()
        for item in nested:
            if name not in item:
                continue

            value = item[name]
            if cast:
                value = mapping['type'](value)
            joined.append(value)
        if joined:
            if rename:
                flat[mapping['name']] = joined
            else:
                flat[name] = joined


def _lap_timings_flatten_by_rename(nested: dict, category: dict, flat: dict, *,
                                   cast: bool = True, rename: bool = True):
    """:meta private:
    Wrapper for :func:`flatten_by_rename` especially for lap timings.
    This function additionally directly integrates the subkey 'Timings' into
    the flattened results and converts the 'number' key to a list of value
    to match the values from 'Timings'.
    """
    # apply the normal flatten_by_rename function
    _flatten_by_rename(nested, category, flat, cast=cast, rename=rename)

    # pop the 'Timings' subcategory from the nested object to process it
    # here on this level already
    subcontent = nested.pop('Timings')
    # call its conversion method on its content to enable renaming and casting
    # by doing so, the subcontent is already directly integrated into flat
    Timings['method'](subcontent, Timings, flat, cast=cast, rename=rename)
    # the subcontent is a list of values for each key while 'number' is a
    # single value; therefore 'number' is augmented to a list of correct length
    flat['number'] = [flat['number'], ] * len(flat['driverId'])


# ################################
# ### root category finalizers ###

def _merge_dicts_of_lists(data):
    """:meta-private:
    Transform a list of equally keyed dictionaries that only contain lists into
    a single dictionary containing these list joined together.

        [
            {'value' : [1, 2, 3], ...},
            {'value' : [4, 5, 6], ...},
            ...
        ]

    Transform to ::

        {'value' : [1, 2, 3, 4, 5, 6, ...], ...},
    """
    if len(data) <= 1:
        return data[0]

    for i in range(len(data) - 1):
        _tmp = data.pop(1)
        for key in data[0].keys():
            data[0][key].extend(_tmp.pop(key))

    return data[0]


# #####################################
# ### response subcategory elements ###

FirstPractice = {
    'name': 'FirstPractice',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'date': {'name': 'fp1Date', 'type': date_from_ergast},
            'time': {'name': 'fp1Time', 'type': time_from_ergast}},
    'sub': [],
    'finalize': None
}

SecondPractice = {
    'name': 'SecondPractice',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'date': {'name': 'fp2Date', 'type': date_from_ergast},
            'time': {'name': 'fp2Time', 'type': time_from_ergast}},
    'sub': [],
    'finalize': None
}

ThirdPractice = {
    'name': 'ThirdPractice',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'date': {'name': 'fp3Date', 'type': date_from_ergast},
            'time': {'name': 'fp3Time', 'type': time_from_ergast}},
    'sub': [],
    'finalize': None
}

Qualifying = {
    'name': 'Qualifying',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'date': {'name': 'qualifyingDate', 'type': date_from_ergast},
            'time': {'name': 'qualifyingTime', 'type': time_from_ergast}},
    'sub': [],
    'finalize': None
}

Sprint = {
    'name': 'Sprint',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'date': {'name': 'sprintDate', 'type': date_from_ergast},
            'time': {'name': 'sprintTime', 'type': time_from_ergast}},
    'sub': [],
    'finalize': None
}

TotalRaceTime = {
    'name': 'Time',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {
        'millis': {'name': 'totalRaceTimeMillis', 'type': int},
        'time': {'name': 'totalRaceTime', 'type': timedelta_from_ergast}
    },
    'sub': [],
    'finalize': None
}

FastestLapTime = {
    'name': 'Time',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {
        'millis': {'name': 'fastestLapTimeMillis', 'type': int},
        'time': {'name': 'fastestLapTime', 'type': timedelta_from_ergast}
    },
    'sub': [],
    'finalize': None
}

FastestLapAvgSpeed = {
    'name': 'AverageSpeed',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'units': {'name': 'fastestLapAvgSpeedUnits', 'type': str},
            'speed': {'name': 'fastestLapAvgSpeed', 'type': float}},
    'sub': [],
    'finalize': None
}

FastestLap = {
    'name': 'FastestLap',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'rank': {'name': 'fastestLapRank', 'type': int},
            'lap': {'name': 'fastestLapNumber', 'type': int}},
    'sub': [FastestLapTime, FastestLapAvgSpeed],
    'finalize': None
}

Driver = {
    'name': 'Driver',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'driverId': {'name': 'driverId', 'type': str},
            'permanentNumber': {'name': 'driverNumber', 'type': int},
            'code': {'name': 'driverCode', 'type': str},
            'url': {'name': 'driverUrl', 'type': str},
            'givenName': {'name': 'givenName', 'type': str},
            'familyName': {'name': 'familyName', 'type': str},
            'dateOfBirth': {'name': 'dateOfBirth', 'type': date_from_ergast},
            'nationality': {'name': 'driverNationality', 'type': str}},
    'sub': [],
    'finalize': None
}

Constructor = {
    'name': 'Constructor',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'constructorId': {'name': 'constructorId', 'type': str},
            'url': {'name': 'constructorUrl', 'type': str},
            'name': {'name': 'constructorName', 'type': str},
            'nationality': {'name': 'constructorNationality', 'type': str}},
    'sub': [],
    'finalize': None
}

ConstructorsInline = {
    # special case for where a list of constructors is given for a single
    # 'element' within the result (example: driver standings with potentially
    # multiple constructors per driver); these are reduced to a list of values
    # for each data field
    'name': 'Constructors',
    'type': list,
    'method': _flatten_inline_list_of_dicts,
    'map': {'constructorId': {'name': 'constructorIds', 'type': str},
            'url': {'name': 'constructorUrls', 'type': str},
            'name': {'name': 'constructorNames', 'type': str},
            'nationality': {'name': 'constructorNationalities', 'type': str}},
    'sub': [],
    'finalize': None
}

Location = {
    'name': 'Location',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'lat': {'name': 'lat', 'type': float},
            'long': {'name': 'long', 'type': float},
            'locality': {'name': 'locality', 'type': str},
            'country': {'name': 'country', 'type': str}},
    'sub': [],
    'finalize': None
}

Circuit = {
    'name': 'Circuit',
    'type': dict,
    'method': _flatten_by_rename,
    'map': {'circuitId': {'name': 'circuitId', 'type': str},
            'url': {'name': 'circuitUrl', 'type': str},
            'circuitName': {'name': 'circuitName', 'type': str}},
    'sub': [Location],
    'finalize': None
}

QualifyingResults = {
    'name': 'QualifyingResults',
    'type': list,
    'method': _flatten_by_rename,
    'map': {'number': {'name': 'number', 'type': int},
            'position': {'name': 'position', 'type': int},
            'Q1': {'name': 'Q1', 'type': timedelta_from_ergast},
            'Q2': {'name': 'Q2', 'type': timedelta_from_ergast},
            'Q3': {'name': 'Q3', 'type': timedelta_from_ergast}},
    'sub': [Driver, Constructor],
    'finalize': None
}

RaceResults = {
    'name': 'Results',
    'type': list,
    'method': _flatten_by_rename,
    'map': {'number': {'name': 'number', 'type': int},
            'position': {'name': 'position', 'type': int},
            'positionText': {'name': 'positionText', 'type': str},
            'points': {'name': 'points', 'type': float},
            'grid': {'name': 'grid', 'type': int},
            'laps': {'name': 'laps', 'type': int},
            'status': {'name': 'status', 'type': str}},
    'sub': [Driver, Constructor, TotalRaceTime, FastestLap,
            FastestLapAvgSpeed],
    'finalize': None
}

SprintResults = {
    **RaceResults,  # generate from _RaceResults
    'name': 'SprintResults'
}

DriverStandings = {
    'name': 'DriverStandings',
    'type': list,
    'method': _flatten_by_rename,
    'map': {'position': {'name': 'position', 'type': int},
            'positionText': {'name': 'positionText', 'type': str},
            'points': {'name': 'points', 'type': float},
            'wins': {'name': 'wins', 'type': int}},
    'sub': [Driver, ConstructorsInline],
    'finalize': None
}

ConstructorStandings = {
    **DriverStandings,  # generate from _DriverStandings
    'name': 'ConstructorStandings',
    'sub': [Constructor]
}

Timings = {
    'name': 'Timings',
    'type': list,
    'method': _flatten_inline_list_of_dicts,
    'map': {'driverId': {'name': 'driverId', 'type': str},
            'position': {'name': 'position', 'type': int},
            'time': {'name': 'time', 'type': timedelta_from_ergast},
            },
    'sub': [],
    'finalize': None
}

Laps = {
    'name': 'Laps',
    'type': list,
    'method': _lap_timings_flatten_by_rename,
    'map': {'number': {'name': 'number', 'type': int}},
    'sub': [Timings],
    'finalize': _merge_dicts_of_lists
}

PitStops = {
    'name': 'PitStops',
    'type': list,
    'method': _flatten_by_rename,
    'map': {'driverId': {'name': 'driverId', 'type': str},
            'stop': {'name': 'stop', 'type': int},
            'lap': {'name': 'lap', 'type': int},
            'time': {'name': 'time', 'type': time_from_ergast},
            'duration': {'name': 'duration', 'type': timedelta_from_ergast}},
    'sub': [Driver, ConstructorsInline],
    'finalize': None
}

# ##############################
# ### response root elements ###

Seasons = {
    'name': 'Seasons',
    'type': list,
    'method': _flatten_by_rename,
    'map': {'season': {'name': 'season', 'type': int},
            'url': {'name': 'seasonUrl', 'type': str}},
    'sub': [],
    'finalize': None
}

__StandingsLists = {
    'name': 'StandingsLists',
    'type': list,
    'method': _flatten_by_rename,
    'map': {'season': {'name': 'season', 'type': int},
            'round': {'name': 'round', 'type': int}},
    'finalize': None
}

StandingsLists_Driver = {
    **__StandingsLists,
    'sub': [DriverStandings]
}

StandingsLists_Constructor = {
    **__StandingsLists,
    'sub': [ConstructorStandings]
}

__Races = {
    # template for all 'Races' based categories
    'name': 'Races',
    'type': list,
    'method': _flatten_by_rename,
    'map': {'season': {'name': 'season', 'type': int},
            'round': {'name': 'round', 'type': int},
            'url': {'name': 'raceUrl', 'type': str},
            'raceName': {'name': 'raceName', 'type': str},
            'date': {'name': 'raceDate', 'type': date_from_ergast},
            'time': {'name': 'raceTime', 'type': time_from_ergast}},
    'finalize': None
}

Races_Schedule = {
    **__Races,
    'sub': [Circuit, FirstPractice, SecondPractice, ThirdPractice,
            Qualifying, Sprint]
}

Races_RaceResults = {
    **__Races,
    'sub': [Circuit, RaceResults],
}

Races_QualifyingResults = {
    **__Races,
    'sub': [Circuit, QualifyingResults]
}

Races_SprintResults = {
    **__Races,
    'sub': [Circuit, SprintResults]
}

Races_Laps = {
    **__Races,
    'sub': [Circuit, Laps]
}

Races_PitStops = {
    **__Races,
    'sub': [Circuit, PitStops]
}

Drivers = {
    **Driver,  # from Driver
    'type': list,
    'name': 'Drivers'
}

Constructors = {
    **Constructor,
    'type': list,
    'name': 'Constructors',
}

Circuits = {
    **Circuit,  # from Circuit
    'type': list,
    'name': 'Circuits'
}

Status = {
    'name': 'Status',
    'type': list,
    'method': _flatten_by_rename,
    'map': {'statusId': {'name': 'statusId', 'type': int},
            'count': {'name': 'count', 'type': int},
            'status': {'name': 'status', 'type': str}},
    'sub': [],
    'finalize': None
}
