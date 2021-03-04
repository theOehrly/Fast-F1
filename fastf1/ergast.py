import json
import requests
import warnings

base_url = 'http://ergast.com/api/f1'


def load(year, gp, session):
    """session can be 'Qualifying' or 'Race'
    mainly to port on upper level libraries
    """
    day = 'qualifying' if session == 'Qualifying' else 'results'
    sel = 'QualifyingResults' if session == 'Qualifying' else 'Results'
    return _parse_ergast(fetch_day(year, gp, day))[0][sel]


def fetch_season(year):
    url = f"{base_url}/{year}.json"
    return _parse_ergast(_parse_json_response(requests.get(url)))


def fetch_weekend(year, gp):
    url = f"{base_url}/{year}/{gp}.json"
    data = _parse_ergast(_parse_json_response(requests.get(url)))[0]
    url = ("https://www.mapcoordinates.net/admin/component/edit/"
           + "Vpc_MapCoordinates_Advanced_GoogleMapCoords_Component/"
           + "Component/json-get-elevation")
    loc = data['Circuit']['Location']
    body = {'longitude': loc['long'], 'latitude': loc['lat']}
    res = _parse_json_response(requests.post(url, data=body))
    data['Circuit']['Location']['alt'] = res['elevation']
    return data


def fetch_day(year, gp, day):
    """day can be 'qualifying' or 'results'
    """
    url = f"{base_url}/{year}/{gp}/{day}.json"
    return _parse_json_response(requests.get(url))


def _parse_json_response(r):
    if r.status_code == 200:
        return json.loads(r.content.decode('utf-8'))
    else:
        warnings.warn(f"Request returned: {r.status_code}")
        return None


def _parse_ergast(data):
    return data['MRData']['RaceTable']['Races']
