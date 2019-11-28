import json
import requests
import requests_cache

base_url = 'https://livetiming.formula1.com'
requests_cache.install_cache('formula1_cache', allowable_methods=('GET', 'POST'))

headers = {
  'Host': 'livetiming.formula1.com',
  #'X-NewRelic-ID': 'VQ8GUlBXCBAEUlBWAgEGUw==',
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
  'race_control_messages': 'RaceControlMessages.json', # SC etc
  'session_status': 'SessionStatus.jsonStream', # Start and finish times
  'team_radio': 'TeamRadio.jsonStream', # Links to team radios
  'timing_app_data': 'TimingAppData.jsonStream', # Tyres and lap story
  'timing_stats': 'TimingStats.jsonStream', # Sectors best and personal
  'track_status': 'TrackStatus.jsonStream',
  'weather_data': 'WeatherData.jsonStream',
  'position': 'Position.z.jsonStream',
  'car_data': 'CarData.z.jsonStream',
  'content_streams': 'ContentStreams.jsonStream',
  'timing_data': 'TimingData.jsonStream',
  'lap_count': 'LapCount.jsonStream',
  'championship_predicion': 'ChampionshipPrediction.jsonStream'
}

def load(name, date, session):
    for name in pages:
        #fetch_page(make_path(name, date, session), name)
        pass

def make_path(wname, d, session):
    smooth_operator = f'{d[:4]}/{d} {wname}/{d} {session}/'.replace(' ', '_')
    return f'/static/{smooth_operator}'
            
def fetch_page(path, name):
    r = requests.get(base_url + path + pages[name], headers=headers)
    if r.status_code == 200:
        return r.content.decode('utf-8')
    else:
        return None

#zlib.decompress(base64.b64decode(t), -zlib.MAX_WBITS)     

