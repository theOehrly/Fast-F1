import os
import logging


def test_enable_cache(tmpdir):
    import fastf1
    fastf1.Cache.enable_cache(tmpdir)


def test_cache_used_and_clear(tmpdir, requests_mock, caplog):
    import fastf1
    import requests

    caplog.set_level(logging.INFO)  # log level for log capturing

    # create a custom requests session here so that requests_mock is
    # properly used
    test_session = requests.session()
    fastf1.api.requests_session = test_session

    # enable fastf1's own pickle cache
    fastf1.Cache.enable_cache(tmpdir)

    # create mock repsonses for general api requests
    with open('fastf1/testing/reference_data/2020_05_FP2/'
              'ergast_race.raw', 'rb') as fobj:
        content = fobj.read()
    requests_mock.get('http://ergast.com/api/f1/2020/5.json',
                      content=content, status_code=200)

    with open('fastf1/testing/reference_data/2020_05_FP2/'
              'ergast_race_result.raw', 'rb') as fobj:
        content = fobj.read()
    requests_mock.get('http://ergast.com/api/f1/2020/5/results.json',
                      content=content, status_code=200)

    with open('fastf1/testing/reference_data/2020_05_FP2/'
              'map_data.raw', 'rb') as fobj:
        content = fobj.read()
    requests_mock.post('https://www.mapcoordinates.net/admin/component/edit/'
                       'Vpc_MapCoordinates_Advanced_GoogleMapCoords_Component/'
                       'Component/json-get-elevation',
                       content=content, status_code=200)

    # rainy and short session, good for fast test/quick loading
    session = fastf1.get_session(2020, 5, 'FP2')

    # create mock responses for f1 api requests
    req_pages = ['timing_data', 'timing_app_data', 'track_status',
                 'session_status', 'car_data', 'position', 'weather_data']
    for p in req_pages:
        with open(f'fastf1/testing/reference_data/2020_05_FP2/{p}.raw', 'rb') as fobj:
            lines = fobj.readlines()

        # ensure correct newline character (as expected by api parser)
        # strip all newline characters and terminate each line with \r\n
        # needs to work despite os and git newline character substitution
        content = b''
        for line in lines:
            content += line.strip(b'\n').strip(b'\r') + b'\r\n'

        path = fastf1.api.base_url + session.api_path + fastf1.api.pages[p]
        requests_mock.get(path, content=content, status_code=200)

    # load the data
    session.load_laps(with_telemetry=True)

    # check cache directory, pickled results should now exist
    cache_dir_path = os.path.join(tmpdir, session.api_path[8:])
    dir_list = os.listdir(cache_dir_path)
    expected_dir_list = ['car_data.ff1pkl', 'position_data.ff1pkl',
                         'session_status_data.ff1pkl',
                         'timing_app_data.ff1pkl', 'timing_data.ff1pkl',
                         'track_status_data.ff1pkl',
                         'weather_data.ff1pkl']
    # test both ways round
    assert all(elem in expected_dir_list for elem in dir_list)
    assert all(elem in dir_list for elem in expected_dir_list)

    # recreate session and reload data
    # this should use the cache this time
    caplog.clear()
    session = fastf1.get_session(2020, 5, 'FP2')
    session.load_laps(with_telemetry=True)
    print(caplog.text)
    assert "Using cached data for" in caplog.text

    fastf1.Cache.clear_cache(tmpdir)  # should delete pickle files
    assert os.listdir(cache_dir_path) == []
