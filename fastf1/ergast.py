import json
import warnings

from fastf1.api import Cache
from fastf1.version import __version__

base_url = 'http://ergast.com/api/f1'
_headers = {'User-Agent': f'FastF1/{__version__}'}


def fetch_results(year, gp, session):
    """session can be 'Qualifying' or 'Race'
    mainly to port on upper level libraries
    """
    if session == 'Race':
        day = 'results'
        sel = 'Results'
    elif session == 'Qualifying':
        day = 'qualifying'
        sel = 'QualifyingResults'
    elif session in ('Sprint Qualifying', 'Sprint'):
        day = 'sprint'
        sel = 'SprintResults'

    return _parse_ergast(fetch_day(year, gp, day))[0][sel]


def fetch_season(year):
    url = f"{base_url}/{year}.json"
    return _parse_ergast(_parse_json_response(
        Cache.requests_get(url, headers=_headers))
    )


def fetch_weekend(year, gp):
    url = f"{base_url}/{year}/{gp}.json"
    data = _parse_ergast(_parse_json_response(
        Cache.requests_get(url, headers=_headers)
    ))[0]
    url = ("https://www.mapcoordinates.net/admin/component/edit/"
           + "Vpc_MapCoordinates_Advanced_GoogleMapCoords_Component/"
           + "Component/json-get-elevation")
    loc = data['Circuit']['Location']
    body = {'longitude': loc['long'], 'latitude': loc['lat']}
    res = _parse_json_response(Cache.requests_post(url, data=body))
    data['Circuit']['Location']['alt'] = res['elevation']
    return data


def fetch_day(year, gp, day):
    """day can be 'qualifying' or 'results'
    """
    url = f"{base_url}/{year}/{gp}/{day}.json"
    return _parse_json_response(Cache.requests_get(url, headers=_headers))


def _parse_json_response(r):
    if r.status_code == 200:
        return json.loads(r.content.decode('utf-8'))
    else:
        warnings.warn(f"Request returned: {r.status_code}")
        return None


def _parse_ergast(data):
    return data['MRData']['RaceTable']['Races']
