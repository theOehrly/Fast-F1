import datetime
import logging
import re


# ### date and time conversion ###

_time_string_matcher = re.compile(
    r'(\d{1,2}:)?(\d{1,2}:)?(\d{1,2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?'
)
# matches [hh:][mm:]ss[.micros][Z | +-hh:mm] timestring


def date_from_ergast(d_str):
    """Create a ``datetime.datetime`` object from a date stamp formatted
    like 'YYYY-MM-DD'."""
    return datetime.datetime.strptime(d_str, "%Y-%m-%d")


def time_from_ergast(t_str):
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

    if res[1] and res[2] and res[3]:
        hour, minute, second = int(res[1][:-1]), int(res[2][:-1]), int(res[3])
    elif res[1] and res[3]:
        hour, minute, second = 0, int(res[1][:-1]), int(res[3])
    elif res[3]:
        hour, minute, second = 0, 0, int(res[3])
    else:
        logging.debug(f"Failed to parse timestamp '{t_str}' in Ergast"
                      f"response.")
        return None

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
        logging.debug(f"Failed to parse timestamp '{t_str}' in Ergast"
                      f"response.")
        return None


def timedelta_from_ergast(t_str):
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


# ### flattening of ergast response data ###


def flatten_by_rename(nested: dict, category: dict, flat: dict, cast: bool):
    """:meta private:
    Iterate over all values on the current level, rename them and
    add them to the flattened result dict. This is the default operation that
    is used for most Ergast responses.

    This function operates inplace on 'nested' and 'flat'.
    """
    for name, mapping in category['map'].items():
        if name not in nested:
            continue

        value = nested[name]
        if cast:
            value = mapping['type'](value)
        flat[mapping['name']] = value


def flatten_inline_list_of_dicts(nested: dict, category: dict, flat: dict,
                                 cast: bool):
    """:meta private:
    The current level is a single list of dictionaries, iterate over them and
    convert from a list of dictionaries::

        "Constructors": [
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
            flat[mapping['name']] = joined


# ### category post-processors ###


def transform_lap_data(data):
    """:meta private:
    Finalizes the flattening of laps data. This is necessary because the
    'Number' value needs to be augmented so that it exists for each lap. Then
    it is possible to drop a nesting dimension.

    Example, data after already performed flattening ::

        [
            {
                'number' : 1,
                'driverId': [alonso, hamilton, ...],
                'time': [...],
                ...
            },{
                'number' : 2,
                'driverId': [alonso, hamilton, ...],
                'time': [...],
                ...
            },
            ...
        ]

    Transform to ::

        {
            'number': [1, 1, ..., 2, 2, ..., ...],
            'driverId': [alonso, hamilton, ..., alonso, hamilton, ..., ...],
            'time': [...],
            ...
        }
    """
    trans = None
    try:
        while data:
            row = data.pop(0)
            length = len(row['driverId'])
            row['number'] = [row['number'], ] * length
            if trans is None:
                trans = row
            else:
                for key, value in row.items():
                    trans[key].extend(value)
    except KeyError:
        logging.warning("Postprocessor on lap timing data failed")
        return None

    return trans


FirstPractice = {
    'name': 'FirstPractice',
    'method': flatten_by_rename,
    'map': {'date': {'name': 'fp1Date', 'type': date_from_ergast},
            'time': {'name': 'fp1Time', 'type': time_from_ergast}},
    'sub': [],
    'post': None
}

SecondPractice = {
    'name': 'SecondPractice',
    'method': flatten_by_rename,
    'map': {'date': {'name': 'fp2Date', 'type': date_from_ergast},
            'time': {'name': 'fp2Time', 'type': time_from_ergast}},
    'sub': [],
    'post': None
}

ThirdPractice = {
    'name': 'ThirdPractice',
    'method': flatten_by_rename,
    'map': {'date': {'name': 'fp3Date', 'type': date_from_ergast},
            'time': {'name': 'fp3Time', 'type': time_from_ergast}},
    'sub': [],
    'post': None
}

Qualifying = {
    'name': 'Qualifying',
    'method': flatten_by_rename,
    'map': {'date': {'name': 'qualifyingDate', 'type': date_from_ergast},
            'time': {'name': 'qualifyingTime', 'type': time_from_ergast}},
    'sub': [],
    'post': None
}

Sprint = {
    'name': 'Sprint',
    'method': flatten_by_rename,
    'map': {'date': {'name': 'sprintDate', 'type': date_from_ergast},
            'time': {'name': 'sprintTime', 'type': time_from_ergast}},
    'sub': [],
    'post': None
}

TotalRaceTime = {
    'name': 'Time',
    'method': flatten_by_rename,
    'map': {
        'millis': {'name': 'totalRaceTimeMillis', 'type': int},
        'time': {'name': 'totalRaceTime', 'type': timedelta_from_ergast}
    },
    'sub': [],
    'post': None
}

FastestLapTime = {
    'name': 'Time',
    'method': flatten_by_rename,
    'map': {
        'millis': {'name': 'fastestLapTimeMillis', 'type': int},
        'time': {'name': 'fastestLapTime', 'type': timedelta_from_ergast}
    },
    'sub': [],
    'post': None
}

FastestLapAvgSpeed = {
    'name': 'AverageSpeed',
    'method': flatten_by_rename,
    'map': {'units': {'name': 'fastestLapAvgSpeedUnits', 'type': str},
            'speed': {'name': 'fastestLapAvgSpeed', 'type': float}},
    'sub': [],
    'post': None
}


FastestLap = {
    'name': 'FastestLap',
    'method': flatten_by_rename,
    'map': {'rank': {'name': 'fastestLapRank', 'type': int},
            'lap': {'name': 'fastestLapNumber', 'type': int}},
    'sub': [FastestLapTime, FastestLapAvgSpeed],
    'post': None
}

Driver = {
    'name': 'Driver',
    'method': flatten_by_rename,
    'map': {'driverId': {'name': 'driverId', 'type': str},
            'permanentNumber': {'name': 'driverNumber', 'type': str},
            'code': {'name': 'driver', 'type': str},
            'url': {'name': 'driverUrl', 'type': str},
            'givenName': {'name': 'givenName', 'type': str},
            'familyName': {'name': 'familyName', 'type': str},
            'dateOfBirth': {'name': 'dateOfBirth', 'type': date_from_ergast},
            'nationality': {'name': 'driverNationality', 'type': str}},
    'sub': [],
    'post': None
}

Constructor = {
    'name': 'Constructor',
    'method': flatten_by_rename,
    'map': {'constructorId': {'name': 'constructorId', 'type': str},
            'url': {'name': 'constructorUrl', 'type': str},
            'name': {'name': 'constructorName', 'type': str},
            'nationality': {'name': 'constructorNationality', 'type': str}},
    'sub': [],
    'post': None
}

ConstructorsInline = {
    # special case for where a list of constructors is given for a single
    # 'element' within the result (example: driver standings with potentially
    # multiple constructors per driver); these are reduced to a list of values
    # for each data field
    **Constructor,
    'name': 'Constructors',
    'method': flatten_inline_list_of_dicts
}

Location = {
    'name': 'Location',
    'method': flatten_by_rename,
    'map': {'lat': {'name': 'lat', 'type': float},
            'long': {'name': 'long', 'type': float},
            'locality': {'name': 'locality', 'type': str},
            'country': {'name': 'country', 'type': str}},
    'sub': [],
    'post': None
}

Circuit = {
    'name': 'Circuit',
    'method': flatten_by_rename,
    'map': {'circuitId': {'name': 'circuitId', 'type': str},
            'url': {'name': 'circuitUrl', 'type': str},
            'circuitName': {'name': 'circuitName', 'type': str}},
    'sub': [Location],
    'post': None
}

QualifyingResults = {
    'name': 'QualifyingResults',
    'method': flatten_by_rename,
    'map': {'number': {'name': 'number', 'type': int},
            'position': {'name': 'position', 'type': int},
            'Q1': {'name': 'Q1', 'type': str},
            'Q2': {'name': 'Q2', 'type': str},
            'Q3': {'name': 'Q3', 'type': str}},
    'sub': [Driver, Constructor],
    'post': None
}

RaceResults = {
    'name': 'Results',
    'method': flatten_by_rename,
    'map': {'number': {'name': 'number', 'type': int},
            'position': {'name': 'position', 'type': int},
            'positionText': {'name': 'positionText', 'type': str},
            'points': {'name': 'points', 'type': int},
            'grid': {'name': 'grid', 'type': int},
            'laps': {'name': 'laps', 'type': int},
            'status': {'name': 'status', 'type': str}},
    'sub': [Driver, Constructor, TotalRaceTime, FastestLap],
    'post': None
}

SprintResults = {
    **RaceResults,  # generate from _RaceResults
    'name': 'SprintResults'
}

DriverStandings = {
    'name': 'DriverStandings',
    'method': flatten_by_rename,
    'map': {'position': {'name': 'position', 'type': int},
            'positionText': {'name': 'positionText', 'type': str},
            'points': {'name': 'points', 'type': int},
            'wins': {'name': 'wins', 'type': int}},
    'sub': [Driver, ConstructorsInline],
    'post': None
}

ConstructorStandings = {
    **DriverStandings,  # generate from _DriverStandings
    'name': 'ConstructorStandings',
    'sub': [Constructor]
}

Timings = {
    'name': 'Timings',
    'method': flatten_inline_list_of_dicts,
    'map': {'driverId': {'name': 'driverId', 'type': str},
            'position': {'name': 'position', 'type': int},
            'time': {'name': 'time', 'type': timedelta_from_ergast}},
    'sub': [],
    'post': None
}

Laps = {
    'name': 'Laps',
    'method': flatten_by_rename,
    'map': {'number': {'name': 'number', 'type': int}},
    'sub': [Timings],
    'post': transform_lap_data
}

PitStops = {
    'name': 'PitStops',
    'method': flatten_by_rename,
    'map': {'driverId': {'name': 'driverId', 'type': str},
            'stop': {'name': 'stop', 'type': int},
            'lap': {'name': 'lap', 'type': int},
            'time': {'name': 'time', 'type': time_from_ergast},
            'duration': {'name': 'duration', 'type': timedelta_from_ergast}},
    'sub': [Driver, ConstructorsInline],
    'post': None
}

# ### response root elements ###

Seasons = {
    'name': 'Seasons',
    'method': flatten_by_rename,
    'map': {'season': {'name': 'season', 'type': int},
            'url': {'name': 'seasonUrl', 'type': str}},
    'sub': [],
    'post': None
}

__StandingsLists = {
    'name': 'StandingsLists',
    'method': flatten_by_rename,
    'map': {'season': {'name': 'season', 'type': int},
            'round': {'name': 'round', 'type': int}},
    'post': None
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
    'method': flatten_by_rename,
    'map': {'season': {'name': 'season', 'type': int},
            'round': {'name': 'round', 'type': int},
            'url': {'name': 'raceUrl', 'type': str},
            'raceName': {'name': 'raceName', 'type': str},
            'date': {'name': 'raceDate', 'type': date_from_ergast},
            'time': {'name': 'raceTime', 'type': time_from_ergast}},
    'post': None
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
    'sub': [Circuit]
}

Races_PitStops = {
    **__Races,
    'sub': [Circuit]
}

Drivers = {
    **Driver,  # from Driver
    'name': 'Drivers'
}

Constructors = {
    **Constructor,
    'name': 'Constructors',
}

Circuits = {
    **Circuit,  # from Circuit
    'name': 'Circuits'
}

Status = {
    'name': 'Status',
    'method': flatten_by_rename,
    'map': {'statusId': {'name': 'statusId', 'type': int},
            'count': {'name': 'count', 'type': int},
            'status': {'name': 'status', 'type': str}},
    'sub': [],
    'post': None
}
