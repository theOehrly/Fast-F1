"""
:mod:`fastf1.api` - Api module
==============================

This module contains the main interfaces to the f1 web api
"""
import json
import base64
import copy
import zlib
import requests
import logging
import pandas as pd
import numpy as np
from fastf1 import utils


base_url = 'https://livetiming.formula1.com'

headers = {
  'Host': 'livetiming.formula1.com',
  'Connection': 'close',
  'Accept': '*/*',
  'User-Agent': 'Formula%201/715 CFNetwork/1120 Darwin/19.0.0',
  'Accept-Language': 'en-us',
  'Accept-Encoding': 'gzip, deflate',
  'X-Unity-Version': '2018.4.1f1'
}

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
  'timing_app_data': 'TimingAppData.jsonStream', # Tyres and laps (juicy)
  'timing_stats': 'TimingStats.jsonStream', # 'Best times/speed' useless
  'track_status': 'TrackStatus.jsonStream', # SC, VSC and Yellow
  'weather_data': 'WeatherData.jsonStream', # Temp, wind and rain
  'position': 'Position.z.jsonStream', # Coordinates, not GPS? (.z)
  'car_data': 'CarData.z.jsonStream', # Telemetry channels (.z)
  'content_streams': 'ContentStreams.jsonStream', # Lap by lap feeds
  'timing_data': 'TimingData.jsonStream', # Gap to car ahead 
  'lap_count': 'LapCount.jsonStream', # Lap counter
  'championship_predicion': 'ChampionshipPrediction.jsonStream' # Points
}
"""Known requests
"""


def make_path(wname, wdate, sname, sdate):
    """Create web path to append on livetiming.formula1.com for api
    requests.

    Args:
        wname: Weekend name (e.g. 'Italian Grand Prix')
        wdate: Weekend date (e.g. '2019-09-08')
        sname: Session name 'Qualifying' or 'Race'
        sdate: Session date (formatted as wdate)
    
    Returns:
        string path
    """
    smooth_operator = f'{wdate[:4]}/{wdate} {wname}/{sdate} {sname}/'
    return '/static/' + smooth_operator.replace(' ', '_')


def timing_data(path):
    """Timing data is a mixed stream of information of each driver.
    At a given time a packet of data may indicate position, lap time,
    speed trap, sector time and so on.

    While most of this data can be mapped lap by lap given a readable and
    usable data structure, other entries like position and time gaps are
    separated and mapped on finer timeseries.
    """
    raw = fetch_page(path, 'timing_data')
    laps_data = _timing_data_laps(path, response=raw)
    stream_data = _timing_data_stream(path, response=raw)
    return laps_data, stream_data


def _timing_data_stream(path, response=None):
    """pre-fetched response can be fed if other functions parse the same
    raw data.
    """
    data, df = {}, None
    if response is None:
        response = fetch_page(path, 'timing_data')
    for entry in response:
        if 'Lines' not in entry[1]:
            continue
        for driver in entry[1]['Lines']:
            if driver not in data:
                data[driver] = {'Time': [], 'Driver': [], 'Position': [],
                                'GapToLeader': [], 'IntervalToPositionAhead':[]}
            time = entry[0]
            block = entry[1]['Lines'][driver]
            new_entry = False

            key = 'Position'
            if key in block:
                data[driver][key].append(block[key])
                new_entry = True
            key = 'GapToLeader'
            if key in block:
                data[driver][key].append(block[key])
                new_entry = True
            key = 'IntervalToPositionAhead'  
            if key in block:
                if 'Value' in block[key]:
                    data[driver][key].append(block[key]['Value'])
                    new_entry = True

            if new_entry:
                data[driver]['Time'].append(time)
                data[driver]['Driver'].append(driver)
                expected_length = len(data[driver]['Time'])
                for key in data[driver]:
                    if len(data[driver][key]) == 0:
                        data[driver][key].append(None)
                    elif len(data[driver][key]) < expected_length:
                        data[driver][key].append(data[driver][key][-1])
    for driver in data:
        data[driver] = pd.DataFrame(data[driver])
        df = data[driver] if df is None else pd.concat([df, data[driver]])
    return df


def _timing_data_laps(path, response=None):
    """pre-fetched response can be fed if other functions parse the same
    raw data.

    """
    if response is None:
        response = fetch_page(path, 'timing_data')
    data, flags, df = {}, {}, None
    for entry in response:
        if 'Lines' not in entry[1]:
            continue
        for driver in entry[1]['Lines']:
            data, flags = _timing_data_laps_entry(entry, driver, data, flags)
    data_cols = [key for key in data[driver] if key not in ['Time', 'Driver']]
    td_cols = ['LastLapTime', 'PitInTime', 'PitOutTime',
               'Sector1Time', 'Sector2Time', 'Sector3Time']
    for driver in data:
        _df = pd.DataFrame(data[driver])
        if not _df.iloc[-1][data_cols].any():
            # Pop last row if all entries are empty
            _df = _df.iloc[:-1]
        # To increase pitstop count on next lap start and not end 
        pit_stops = _df['NumberOfPitStops'].max()
        _df['NumberOfPitStops'] -= 1
        pit_laps = _df[~_df['NumberOfPitStops'].isnull()].index
        for lap in (pit_laps.to_list() + [len(_df)])[::-1]:
            # Going in reverse to spot easily if this messes up
            # (Should always have 0 pitstops at start)
            _df.loc[_df.index <= lap, 'NumberOfPitStops'] = pit_stops
            pit_stops -= 1
        for col in td_cols:
            try:
                _df[col] = _df[col].astype('timedelta64[ns]')
            except:
                continue
        df = _df if df is None else pd.concat([df, _df])
    return df


def _timing_data_laps_entry(entry, driver, data={}, flags={}):
    if driver not in data:
        data[driver] = {'Time': [], 'Driver': [], 'LastLapTime':[],
                        'NumberOfLaps':[], 'NumberOfPitStops': [],
                        'PitOutTime': [], 'PitInTime': [], 'Sector1Time':[],
                        'Sector2Time': [], 'Sector3Time': [], 'SpeedI1': [],
                        'SpeedI2': [], 'SpeedFL': [], 'SpeedST':[]}
        [data[driver][key].append(None) for key in data[driver]]
    if driver not in flags:
        flags[driver] = {'time_reference': [None], 'locked_times': [False]}

    time = __to_time(entry[0])
    block = entry[1]['Lines'][driver]

    # i is the row index that this block has to populate. The
    # arrival of information is a bit randomic. It is assumed that
    # if something arrives 5s after a new record is created, it
    # still belongs to the lap before
    i = -1
    if len(data[driver]['Time']) > 1:
        last_time = data[driver]['Time'][-2]
        if time < (last_time + __to_time('5.000')):
            i = -2

    no_time_reference = flags[driver]['time_reference'][i] is None
    no_locked_time = not flags[driver]['locked_times'][i]
    # Final word on time remains to NumberOfLaps, but this
    # keeps also the last entry populated (in quali can be inlap)
    if no_locked_time:
        data[driver]['Time'][-1] = time
    data[driver]['Driver'][i] = driver

    # The easy one
    if 'NumberOfPitStops' in block:
        data[driver]['NumberOfPitStops'][i] = block['NumberOfPitStops']

    # Sectors are flattened on three separated series
    if 'Sectors' in block:
        # Sectors is a list only if all three are present
        for _n, sector in enumerate(block['Sectors']):
            if isinstance(block['Sectors'], dict):
                # For this trip of pure consistency, we have that
                # sometimes Sectors is a list, so it will be... 
                _n = int(sector)
                sector = block['Sectors'][str(_n)]
            if 'Value' in sector:
                sector_time = __to_time(sector['Value'])
                data[driver][f'Sector{str(_n+1)}Time'][i] = sector_time

            # Sectors are used to calculate the sacred time reference.
            # Following block has the only purpose to find the time with
            # minimum measure delay. Otherwise laps will be out of sync
            has_measure = 'Value' in sector and sector['Value'] != ''
            if _n == 0 and has_measure and no_time_reference:
                flags[driver]['time_reference'][i] = {'base': time,
                                                      'delta': sector_time,
                                                      'ts0': sector_time}
            reference_has_ts0 = (not no_time_reference
                                 and 'ts0' in flags[driver]['time_reference'][i])
            if _n == 1 and has_measure and reference_has_ts0:
                old_reference = (flags[driver]['time_reference'][i]['base']
                                 - flags[driver]['time_reference'][i]['delta'])
                new_delta = (sector_time 
                             + flags[driver]['time_reference'][i]['ts0'])
                new_reference = time - new_delta
                if new_reference < old_reference:
                    flags[driver]['time_reference'][i]['base'] = time
                    flags[driver]['time_reference'][i]['delta'] = new_delta
                flags[driver]['time_reference'][i]['ts1'] = sector_time
            reference_has_ts01 = (reference_has_ts0
                                  and 'ts1' in flags[driver]['time_reference'][i])
            if _n == 2 and has_measure and reference_has_ts01:
                old_reference = (flags[driver]['time_reference'][i]['base']
                                 - flags[driver]['time_reference'][i]['delta'])
                new_delta = (sector_time 
                             + flags[driver]['time_reference'][i]['ts1']
                             + flags[driver]['time_reference'][i]['ts0'])
                new_reference = time - new_delta
                if new_reference < old_reference:
                    flags[driver]['time_reference'][i]['base'] = time
                    flags[driver]['time_reference'][i]['delta'] = new_delta
                flags[driver]['time_reference'][i]['ts2'] = sector_time

    # Same for speed traps
    if 'Speeds' in block:
        for trap in block['Speeds']:
            if 'Value' in block['Speeds'][trap]:
                speedtrap_value = block['Speeds'][trap]['Value']
                data[driver][f'Speed{trap}'][i] = speedtrap_value

    # F1 Reports start and end time of InPit and PitOut
    # To simplify these are reduced to a single pit in start
    # and pit out end time
    if 'InPit' in block and block['InPit'] == False:
        data[driver]['PitOutTime'][i] = time
    if 'InPit' in block and block['InPit'] == True:
        data[driver]['PitInTime'][i] = time

    # Populate LastLapTime only if value is given sometimes it
    # tells it was personal best or something but nobody cares
    # just use .min() This is the last entry of a lap usually.
    if ('LastLapTime' in block
        and 'Value' in block['LastLapTime']
        and block['LastLapTime']['Value'] != ''):
            lap_time = __to_time(block['LastLapTime']['Value'])
            # Pandas here is very smart (i guess?) because even if I 
            # append None it will be guessed as NaT to keep datatype
            # consistency. Very silent behaviour though.
            # UNLESS, no time has been set by this guy (shit #1)
            data[driver]['LastLapTime'][i] = lap_time
            # Tricky tricks to discover with 'accuracy'
            # when lap time has been set
            time_ref = flags[driver]['time_reference'][i]
            if time_ref is not None: 
                lap_start_time = time_ref['base'] - time_ref['delta']
                data[driver]['Time'][i] = lap_start_time + lap_time 
                flags[driver]['locked_times'][i] = True

    # Number of laps triggers a new entry it looks like always
    # comes before LastLapTime.
    # Unless bottas qualifies under red flag in Monza but is later 
    # convalidated, but we are bullet proof against that as well, apart
    # pit stop time. sorry.
    if ('NumberOfLaps' in block):
        data[driver]['NumberOfLaps'][-1] = block['NumberOfLaps']
        [data[driver][key].append(None) for key in data[driver]]
        # prevent shit #1 and put a NaT
        data[driver]['LastLapTime'][-1] = __to_time('') 
        flags[driver]['time_reference'].append(None)
        flags[driver]['locked_times'].append(False)

    return data, flags


def timing_app_data(path, response=None):
    """Full parse of timing app data. This parsing is quite ignorant,
    with  minimum logic just to fix data structure inconsistencies. Tyre
    information is passed to the summary table.
    """
    if response is None:
        response = fetch_page(path, 'timing_app_data')
    data = {'LapNumber': [],'Driver': [], 'LapTime': [], 'Stint': [],
            'TotalLaps': [], 'Compound': [], 'New': [],
            'TyresNotChanged': [], 'Time': [], 'LapFlags': [],
            'LapCountTime': [], 'StartLaps': [], 'Outlap': []}
    for entry in response:
        time = __to_time(entry[0])
        row = entry[1]
        for driver_number in row['Lines']:
            if 'Stints' in row['Lines'][driver_number]:
                update = row['Lines'][driver_number]['Stints']
                for stint_number, stint in enumerate(update):
                    if isinstance(update, dict):
                        stint_number = int(stint)
                        stint = update[stint]
                    for key in data:
                        if key in stint:
                            data[key].append(stint[key])
                        else:
                            data[key].append(None)
                    for key in stint:
                        if key not in data:
                            # Just for debug, maybe remove one day?
                            print(f"{key} not in data!")
                    data['Time'][-1] = time
                    data['Driver'][-1] = driver_number
                    data['Stint'][-1] = stint_number
    return pd.DataFrame(data)


def car_data(path):
    """Fetch and create pandas dataframe for each driver containing
    Telemetry data.

    Samples are not synchronised with the other dataframes and sampling
    time is not constant, usually 240ms but sometimes can be ~270ms.
    Keep absolute reference.

    Useful columns:
        - Date: sample pandas datetime
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
    data, main_structure = {}, {'Date': [],'Time': []}
    [main_structure.update({index[i]: []}) for i in index]
    logging.info("Fetching car data") 
    raw = fetch_page(path, 'car_data')
    logging.info("Parsing car data") 
    date_format = "%Y-%m-%dT%H:%M:%S.%f%z"
    for line in raw:
        time = __to_time(line[0])
        for entry in line[1]['Entries']:
            cars = entry['Cars']
            date = pd.to_datetime(entry['Utc'], format=date_format)
            for driver in cars:
                if driver not in data:
                    data[driver] = copy.deepcopy(main_structure)
                data[driver]['Time'].append(time)
                data[driver]['Date'].append(date)
                for key in index:
                    value = cars[driver]['Channels'][key]
                    data[driver][index[key]].append(value)
    for driver in data:
        data[driver] = pd.DataFrame(data[driver])
    return data


def position(path):
    """Fetch and create pandas dataframe for Position.

    Samples are not synchronised with the other dataframes and sampling
    time is not constant, usually 300ms but sometimes can be ~200ms.
    Keep absolute reference.

    Useful columns:
        - Date: pandas datetime of sample
        - Driver: driver identifier
        - X, Y, Z: Position coordinates

    Args:
        path: web path for base_url, see :func:`make_path`

    Returns:
        pandas dataframe
    """

    index = {'Status': 'Status', 'X': 'X', 'Y': 'Y', 'Z': 'Z'}
    data, main_structure = {}, {'Date': [],'Time': []}
    [main_structure.update({index[i]: []}) for i in index]
    logging.info("Fetching position") 
    raw = fetch_page(path, 'position')
    logging.info("Parsing position") 
    if raw is None:
        return {}
    for line in raw:
        time = __to_time(line[0])
        for entry in line[1]['Position']:
            cars = entry['Entries']
            date = pd.to_datetime(entry['Timestamp'][:-1],
                                  format="%Y-%m-%dT%H:%M:%S.%f",
                                  infer_datetime_format=True)
            for driver in cars:
                if driver not in data:
                    data[driver] = copy.deepcopy(main_structure)
                data[driver]['Time'].append(time)
                data[driver]['Date'].append(date)
                for key in index:
                    data[driver][index[key]].append(cars[driver][key])
                if str(cars[driver]['Status']).isdigit():
                    # Fallback on older api status mapping and convert
                    int_val = data[driver]['Status'][-1] 
                    new_map = 'OffTrack' if int_val else 'OnTrack'
                    data[driver]['Status'][-1] = new_map
    for driver in data:
        data[driver] = pd.DataFrame(data[driver])
    return data


def fetch_page(path, name):
    """Fetch formula1 web api, given url path and page name. An attempt
    to parse json or decode known messages is made.

    Args:
        path: url path (see :func:`make_path`)
        name: page name (see :attr:`pages`)

    Returns:
        dictionary if content was json, list of entries if jsonStream,
        where each element is len 2: [clock, content]. Content is
        parsed with :func:`parse`. None if request failed.

    """
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
    """Parse json and jsonStream as known from livetiming.formula1.com
    """
    if text[0] == '{':
        return json.loads(text)
    if text[0] == '"':
        text = text.strip('"')
    if zipped:
        text = zlib.decompress(base64.b64decode(text), -zlib.MAX_WBITS)
        return parse(text.decode('utf-8-sig'))
    logging.warning("Couldn't parse text")
    return text


def _json_inspector(obj, start=None):
    """This function builds a unique data structure from any jsonStream,
    it allows further inspection for debug/features.

    Args:
        obj: structure returned from fetch_page, usually array 

    Returns:
        dictionary

    """
    structure = obj if start is None else start
    if isinstance(obj, list):
        structure = [{}]
        for e in obj:
            structure[0] = json_inspector(e, start=structure[0])
        return structure
    elif isinstance(obj, dict):
        for key in obj:
            if key not in structure:
                try:
                    structure[key] = {}
                except:
                    print("Inconsistent structure")
                    return None
            structure[key] = json_inspector(obj[key], start=structure[key])
        return structure
    return obj


def __to_time(x):
    if len(x) and isinstance(x, str):
        return pd.to_timedelta('00:00:00.000'[:-len(x)] + x)
    return pd.to_timedelta(x)
