import json
import requests
import requests_cache

base_url = 'https://livetiming.formula1.com'
requests_cache.install_cache('formula1_cache', allowable_methods=('GET', 'POST'))

headers = {
        'Host': 'livetiming.formula1.com',
#        'X-NewRelic-ID': 'VQ8GUlBXCBAEUlBWAgEGUw==',
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
        'heartbeat': 'Hearbeat.jsonStream',
        'audio_streams': 'AudioStreams.jsonStream',
        'driver_list': 'DriverList.jsonStream',
        'extrapolated_clock': 'ExtrapolatedClock.jsonStream',
        'race_control_messages': 'RaceControlMessages.jsonStream',
        'session_info': 'SessionInfo.jsonStream',
        'session_status': 'SessionStatus.jsonStream',
        'team_radio': 'TeamRadio.jsonStream',
        'timing_app_data': 'TimingAppData.jsonStream',
        'timing_stats': 'TimingStats.jsonStream',
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
    path = f'/static/{date[:4]}/{date} {name}/{date} {session}/'.replace(' ', '_') 
    for name in pages:
        r = requests.get(base_url + path + pages[name], headers=headers)
        print(r.status_code)
        print(r.content.decode('utf-8'))
