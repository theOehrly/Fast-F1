import os
import json
import base64
import zlib
import requests
import requests_cache
import logging
import functools
import pandas as pd

base_url = 'https://livetiming.formula1.com'
requests_cache.install_cache('formula1_cache', allowable_methods=('GET', 'POST'))

headers = {
  'Host': 'livetiming.formula1.com',
  'Connection': 'close',
  'Accept': '*/*',
  'User-Agent': 'Formula%201/715 CFNetwork/1120 Darwin/19.0.0',
  'Accept-Language': 'en-us',
  'Accept-Encoding': 'gzip, deflate',
  'X-Unity-Version': '2018.4.1f1'
}

"""Some notes on notation
- line: driver position
"""

pages = {
  'session_info': 'SessionInfo.json', # more rnd
  'archive_status': 'ArchiveStatus.json', # rnd=1880327548
  'heartbeat': 'Heartbeat.jsonStream', # Probably time sinchronization?
  'audio_streams': 'AudioStreams.jsonStream', # Link to audio commentary
  'driver_list': 'DriverList.jsonStream', # Driver info and line story
  'extrapolated_clock': 'ExtrapolatedClock.jsonStream', # Boolean
  'race_control_messages': 'RaceControlMessages.json', # Flags etc
  'session_status': 'SessionStatus.jsonStream', # Start and finish times
  'team_radio': 'TeamRadio.jsonStream', # Links to team radios
  'timing_app_data': 'TimingAppData.jsonStream', # Tyres and lap times
  'timing_stats': 'TimingStats.jsonStream', # Sector times and top speed 
  'track_status': 'TrackStatus.jsonStream', # SC, VSC and Yellow
  'weather_data': 'WeatherData.jsonStream', # Temp, wind and rain
  'position': 'Position.z.jsonStream', # Coordinates, not GPS? (.z)
  'car_data': 'CarData.z.jsonStream', # Telemetry channels (.z)
  'content_streams': 'ContentStreams.jsonStream', # Lap by lap feeds
  'timing_data': 'TimingData.jsonStream', # Gap to car ahead 
  'lap_count': 'LapCount.jsonStream', # Lap counter
  'championship_predicion': 'ChampionshipPrediction.jsonStream' # Points
}

def _cached_panda(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        path = args[0]
        name = func.__name__
        pkl = f"{cache_path}/{'_'.join(path.split('/')[-3:-1])}_{name}.pkl"
        if os.path.isfile(pkl):
            df = pd.read_pickle(pkl)
        else:
            df = func(*args, **kwargs)
            df.to_pickle(pkl)
        return df
    cache_path = './F1_Data'
    os.makedirs(cache_path, exist_ok=True)
    return decorator


def load(name, date, session):
    for name in pages:
        #fetch_page(make_path(name, date, session), name)
        pass


def make_path(wname, d, session):
    """Create web path to append on livetiming.formula1.com for api
    requests.

    Args:
        wname: Weekend name (e.g. 'Italian Grand Prix')
        d: Weekend date (e.g. '2019-09-08')
        session: 'Qualifying' or 'Race'
    
    Returns:
        string path
    """
    if session == 'Qualifying':
        # Assuming that quali was one day before race... well not always
        # Should check if also formula1 makes this assumption
        d_real = (pd.to_datetime(d) + pd.DateOffset(-1)).strftime('%Y-%m-%d')
    else:
        d_real = d
    smooth_operator = f'{d[:4]}/{d} {wname}/{d_real} {session}/'
    return '/static/' + smooth_operator.replace(' ', '_')


@_cached_panda
def car_data(path):
    """Fetch and create pandas dataframe for Telemetry. Cached data is
    used if already fetched.

    Samples are not synchronised with the other dataframes

    Useful columns:
        - Time: sample pandas datetime
        - Driver: driver identifier
        - Speed: Km/h
        - RPM, Gear
        - Throttle, Brake: 0-100 (don't trust brake too much)
        - DRS: Off, Available, Active

    Returns:
        pandas dataframe
    """
    index = {'0': 'RPM', '2': 'Speed', '3': 'nGear',
             '4': 'Throttle', '5': 'Brake', '45': 'DRS'}
    data = {'Time': [],'Date': [], 'Driver': []}
    [data.update({index[i]: []}) for i in index]
    logging.info("Fetching car data") 
    raw = fetch_page(path, 'car_data')
    logging.info("Parsing car data") 
    for line in raw:
        for entry in line[1]['Entries']:
            cars = entry['Cars']
            date = pd.to_datetime(entry['Utc'], format="%Y-%m-%dT%H:%M:%S.%f%z")
            for car in cars:
                data['Clock'].append(line[0])
                data['Time'].append(date)
                data['Driver'].append(car)
                [data[index[i]].append(cars[car]['Channels'][i]) for i in index]
    return pd.DataFrame(data)


@_cached_panda
def position(path):
    """Fetch and create pandas dataframe for Position. Cached data is
    used if already fetched.

    Samples are not synchronised with the other dataframes

    Useful columns:
        - Time: pandas datetime of sample
        - Driver: driver identifier
        - X, Y, Z: Position coordinates

    Args:
        path: web path for base_url, see :func:`make_path`

    Returns:
        pandas dataframe
    """
    index = {'Status': 'Status', 'X': 'X', 'Y': 'Y', 'Z': 'Z'}
    data = {'Time': [],'Date': [], 'Driver': []}
    [data.update({index[i]: []}) for i in index]
    logging.info("Fetching position") 
    raw = fetch_page(path, 'position')
    logging.info("Parsing position") 
    for line in raw:
        for entry in line[1]['Position']:
            cars = entry['Entries']
            date = pd.to_datetime(entry['Timestamp'], format="%Y-%m-%dT%H:%M:%S.%f%z")
            for car in cars:
                data['Clock'].append(line[0])
                data['Time'].append(date)
                data['Driver'].append(car)
                [data[index[i]].append(cars[car][i]) for i in index]
    return pd.DataFrame(data)


def fetch_page(path, name):
    page = pages[name]
    is_stream = 'jsonStream' in page
    is_z = '.z.' in page
    r = requests.get(base_url + path + pages[name], headers=headers)
    if r.status_code == 200:
        raw = r.content.decode('utf-8-sig')
        if is_stream:
            tl = len('00:00:00:000')
            entries = raw.split('\r\n')[:-1] # last split is empty
            return [[e[:tl], parse(e[tl:], zipped=is_z)] for e in entries]
        else:
            return parse(raw, is_z)
    else:
        return None


def parse(text, zipped=False):
    if text[0] == '{':
        return json.loads(text)
    if text[0] == '"':
        text = text.strip('"')
    if zipped:
        text = zlib.decompress(base64.b64decode(text), -zlib.MAX_WBITS)
        return parse(text.decode('utf-8-sig'))
    logging.warning("Couldn't parse text")
    return text

