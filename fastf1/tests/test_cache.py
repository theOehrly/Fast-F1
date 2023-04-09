import logging
import os

from fastf1 import Cache
import fastf1.testing


def test_enable_cache(tmpdir):
    fastf1.testing.run_in_subprocess(_test_enable_cache, tmpdir)


def _test_enable_cache(tmpdir):
    Cache.enable_cache(tmpdir)


def test_cache_used_and_clear(tmpdir):
    fastf1.testing.run_in_subprocess(_test_cache_used_and_clear, tmpdir)


def _test_cache_used_and_clear(tmpdir):
    # this test requires using requests_mock to allow running offline
    # other tests can depend on fastf1's internal cache (which is tested here)
    # for offline running, after they've had one online run
    import fastf1
    import requests_mock

    with requests_mock.Mocker() as mocker:
        # create a custom requests session here so that requests_mock is
        # properly used

        # enable fastf1's own pickle cache
        Cache.enable_cache(tmpdir, use_requests_cache=False)

        with open('fastf1/testing/reference_data/'
                  'Index2020.json', 'rb') as fobj:
            content = fobj.read()
        mocker.get('https://livetiming.formula1.com/static/2020/Index.json',
                   content=content, status_code=200)

        # create mock repsonses for general api requests
        with open('fastf1/testing/reference_data/2020_05_FP2/'
                  'ergast_race.raw', 'rb') as fobj:
            content = fobj.read()
        mocker.get('https://ergast.com/api/f1/2020/5.json',
                   content=content, status_code=200)

        with open('fastf1/testing/reference_data/2020_05_FP2/'
                  'ergast_race_result.raw', 'rb') as fobj:
            content = fobj.read()
        mocker.get('https://ergast.com/api/f1/2020/5/results.json',
                   content=content, status_code=200)

        # rainy and short session, good for fast test/quick loading
        session = fastf1.get_session(2020, 5, 'FP2')

        # create mock responses for f1 api requests
        req_pages = ['timing_data', 'timing_app_data', 'track_status',
                     'session_status', 'car_data', 'position',
                     'weather_data', 'driver_list', 'race_control_messages']
        for p in req_pages:
            with open(f'fastf1/testing/reference_data/'
                      f'2020_05_FP2/{p}.raw', 'rb') as fobj:
                lines = fobj.readlines()

            # ensure correct newline character (as expected by api parser)
            # strip all newline characters and terminate each line with \r\n
            # needs to work despite os and git newline character substitution
            content = b''
            for line in lines:
                content += line.strip(b'\n').strip(b'\r') + b'\r\n'

            path = fastf1.api.base_url + session.api_path + fastf1.api.pages[p]
            mocker.get(path, content=content, status_code=200)

        # load the data
        session.load()

        # check cache directory, pickled results should now exist
        cache_dir_path = os.path.join(tmpdir, session.api_path[8:])
        dir_list = os.listdir(cache_dir_path)
        expected_dir_list = ['car_data.ff1pkl', 'position_data.ff1pkl',
                             'driver_info.ff1pkl',
                             'session_status_data.ff1pkl',
                             'timing_app_data.ff1pkl', 'timing_data.ff1pkl',
                             'track_status_data.ff1pkl',
                             'weather_data.ff1pkl',
                             'race_control_messages.ff1pkl']
        # test both ways round
        assert all(elem in expected_dir_list for elem in dir_list)
        assert all(elem in dir_list for elem in expected_dir_list)

        # recreate session and reload data
        # this should use the cache this time
        log_handle = fastf1.testing.capture_log(logging.INFO)
        session = fastf1.get_session(2020, 5, 'FP2')
        session.load()
        assert "Using cached data for" in log_handle.text

        Cache.clear_cache(tmpdir)  # should delete pickle files
        assert os.listdir(cache_dir_path) == []
