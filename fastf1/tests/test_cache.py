import logging
import os

import pytest

import fastf1._api
import fastf1.ergast.interface
import fastf1.testing
from fastf1 import Cache
from fastf1.logger import LoggingManager


def test_enable_cache(tmpdir):
    fastf1.testing.run_in_subprocess(_test_enable_cache, tmpdir)


def _test_enable_cache(tmpdir):
    Cache.configure(cache_dir=tmpdir)


def test_cache_used_and_clear(tmpdir):
    fastf1.testing.run_in_subprocess(_test_cache_used_and_clear, tmpdir,
                                     use_default_cache=False)


def _test_cache_used_and_clear(tmpdir):
    # this test requires using requests_mock to allow running offline
    # other tests can depend on fastf1's internal cache (which is tested here)
    # for offline running, after they've had one online run
    import requests_mock

    import fastf1

    with requests_mock.Mocker() as mocker:
        # create a custom requests session here so that requests_mock is
        # properly used

        # enable fastf1's own pickle cache
        Cache.configure(cache_dir=tmpdir, use_requests_cache=False)

        with open('fastf1/testing/data/cache_test/'
                  'schedule_2020.json', 'rb') as fobj:
            content = fobj.read()
        mocker.get('https://raw.githubusercontent.com/theOehrly/f1schedule/'
                   'master/schedule_2020.json',
                   content=content, status_code=200)

        with open('fastf1/testing/data/cache_test/'
                  'Index2020.json', 'rb') as fobj:
            content = fobj.read()
        mocker.get('https://livetiming.formula1.com/static/2020/Index.json',
                   content=content, status_code=200)

        # create mock responses for general api requests
        with open('fastf1/testing/data/cache_test/'
                  'ergast_race.raw', 'rb') as fobj:
            content = fobj.read()
        mocker.get(f'{fastf1.ergast.interface.BASE_URL}/2020/5.json',
                   content=content, status_code=200)

        with open('fastf1/testing/data/cache_test/'
                  'ergast_race_result.raw', 'rb') as fobj:
            content = fobj.read()
        mocker.get(f'{fastf1.ergast.interface.BASE_URL}/2020/5/results.json',
                   content=content, status_code=200)

        # rainy and short session, good for fast test/quick loading
        session = fastf1.get_session(2020, 5, 'FP2')

        # create mock responses for f1 api requests
        req_pages = ['timing_data', 'timing_app_data', 'track_status',
                     'session_status', 'car_data', 'position',
                     'weather_data', 'driver_list', 'race_control_messages',
                     'session_info']
        for p in req_pages:
            with open(f'fastf1/testing/data/'
                      f'cache_test/{p}.raw', 'rb') as fobj:
                lines = fobj.readlines()

            # ensure correct newline character (as expected by api parser)
            # strip all newline characters and terminate each line with \r\n
            # needs to work despite os and git newline character substitution
            content = b''
            for line in lines:
                content += line.strip(b'\n').strip(b'\r') + b'\r\n'

            path = fastf1._api.base_url \
                + session.api_path \
                + fastf1._api.pages[p]

            mocker.get(path, content=content, status_code=200)

        # load the data
        session.load()

        # check cache directory, pickled results should now exist
        cache_dir_path = os.path.join(tmpdir, session.api_path[8:])
        dir_list = os.listdir(cache_dir_path)
        expected_dir_list = ['car_data.ff1pkl', 'position_data.ff1pkl',
                             'driver_info.ff1pkl',
                             'session_status_data.ff1pkl',
                             'timing_app_data.ff1pkl',
                             '_extended_timing_data.ff1pkl',
                             'track_status_data.ff1pkl',
                             'weather_data.ff1pkl',
                             'race_control_messages.ff1pkl',
                             'session_info.ff1pkl']
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


@pytest.mark.skipif(fastf1.testing.CREATE_HTTP_CACHE,
                    reason="requests are not served from the cache while the "
                           "frozen data is being recorded")
def test_offline_cache_miss_is_collected():
    fastf1.testing.run_in_subprocess(_test_offline_cache_miss_is_collected)


def _test_offline_cache_miss_is_collected():
    # The test suite and the documentation build both rely on
    # OfflineCacheMissHandler to detect data that is missing from the frozen
    # datasets. A build that silently stops collecting misses would publish
    # incomplete results, therefore the connection between fastf1.req and the
    # handler is tested explicitly. (Runs in a subprocess, so that this
    # intentional miss is not reported for the test run itself.)
    import logging

    import fastf1.req
    import fastf1.testing

    handler = fastf1.testing.OfflineCacheMissHandler()
    logging.getLogger("fastf1").addHandler(handler)

    url = "https://fastf1.dev/static/does-not-exist.json"
    response = fastf1.req.Cache.requests_get(url)

    assert response.status_code == 504  # returned by requests-cache on a miss
    assert handler.missed_urls == {url}


# The following tests cover the url fallback of ``Cache.requests_get``. They
# are fully synthetic: all requests are answered by requests_mock and the
# responses are cached in a temporary cache. (Run in a subprocess, because the
# cache configuration is global.)
_PRIMARY_URL = "https://primary.fastf1.dev/data.json"
_MIRROR_URL = "https://mirror.fastf1.dev/data.json"


def test_requests_empty_url_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        Cache.requests_get([])
    with pytest.raises(ValueError, match="must not be empty"):
        Cache.requests_get("")


def test_fallback_on_error_response(tmpdir):
    fastf1.testing.run_in_subprocess(_test_fallback_on_error_response,
                                     tmpdir, use_default_cache=False)


def _test_fallback_on_error_response(tmpdir):
    import requests_mock

    Cache.configure(cache_dir=tmpdir)

    with requests_mock.Mocker() as mocker:
        primary = mocker.get(_PRIMARY_URL, status_code=404)
        mirror = mocker.get(_MIRROR_URL, content=b"mirror", status_code=200)

        log_handle = fastf1.testing.capture_log(logging.DEBUG)
        response = Cache.requests_get((_PRIMARY_URL, _MIRROR_URL))

    assert response.status_code == 200
    assert response.content == b"mirror"
    assert primary.call_count == 1
    assert mirror.call_count == 1
    assert f"Falling back to {_MIRROR_URL}" in log_handle.text


def test_no_fallback_on_success(tmpdir):
    fastf1.testing.run_in_subprocess(_test_no_fallback_on_success,
                                     tmpdir, use_default_cache=False)


def _test_no_fallback_on_success(tmpdir):
    import requests_mock

    Cache.configure(cache_dir=tmpdir)

    with requests_mock.Mocker() as mocker:
        mocker.get(_PRIMARY_URL, content=b"primary", status_code=200)
        mirror = mocker.get(_MIRROR_URL, content=b"mirror", status_code=200)

        log_handle = fastf1.testing.capture_log(logging.DEBUG)
        response = Cache.requests_get((_PRIMARY_URL, _MIRROR_URL))

    assert response.content == b"primary"
    assert mirror.call_count == 0
    assert "Falling back" not in log_handle.text


def test_fallback_all_fail_returns_last_response(tmpdir):
    fastf1.testing.run_in_subprocess(
        _test_fallback_all_fail_returns_last_response,
        tmpdir, use_default_cache=False
    )


def _test_fallback_all_fail_returns_last_response(tmpdir):
    import requests_mock

    Cache.configure(cache_dir=tmpdir)

    with requests_mock.Mocker() as mocker:
        mocker.get(_PRIMARY_URL, status_code=404)
        mocker.get(_MIRROR_URL, status_code=500)

        response = Cache.requests_get((_PRIMARY_URL, _MIRROR_URL))

    assert response.status_code == 500


def test_offline_fallback_to_cached_mirror(tmpdir):
    fastf1.testing.run_in_subprocess(_test_offline_fallback_to_cached_mirror,
                                     tmpdir, use_default_cache=False)


def _test_offline_fallback_to_cached_mirror(tmpdir):
    # A miss for the primary url is irrelevant if the mirror can be served
    # from the cache. Therefore, it must not be reported.
    import requests_mock

    handler = fastf1.testing.OfflineCacheMissHandler()
    logging.getLogger("fastf1").addHandler(handler)

    Cache.configure(cache_dir=tmpdir)

    with requests_mock.Mocker() as mocker:
        # cache a response for the mirror only
        mocker.get(_MIRROR_URL, content=b"mirror", status_code=200)
        Cache.requests_get(_MIRROR_URL)

        Cache.offline_mode(True)
        response = Cache.requests_get((_PRIMARY_URL, _MIRROR_URL))

    assert response.status_code == 200
    assert response.content == b"mirror"
    assert handler.missed_urls == set()


def test_offline_cache_miss_all_urls(tmpdir):
    fastf1.testing.run_in_subprocess(_test_offline_cache_miss_all_urls,
                                     tmpdir, use_default_cache=False)


def _test_offline_cache_miss_all_urls(tmpdir):
    # If no url can be served from the cache, the miss is reported only once
    # and for the first url.
    import requests_mock

    handler = fastf1.testing.OfflineCacheMissHandler()
    logging.getLogger("fastf1").addHandler(handler)

    Cache.configure(cache_dir=tmpdir)
    Cache.offline_mode(True)

    with requests_mock.Mocker():
        log_handle = fastf1.testing.capture_log(logging.WARNING)
        response = Cache.requests_get((_PRIMARY_URL, _MIRROR_URL))

    assert response.status_code == 504  # returned by requests-cache on a miss
    assert handler.missed_urls == {_PRIMARY_URL}
    assert log_handle.text.count("no cached response is available") == 1


def test_fallback_without_requests_cache(tmpdir):
    fastf1.testing.run_in_subprocess(_test_fallback_without_requests_cache,
                                     tmpdir, use_default_cache=False)


def _test_fallback_without_requests_cache(tmpdir):
    # Without the requests cache, a 504 is a genuine server response and not a
    # cache miss. It must neither crash nor be reported as a miss.
    import requests_mock

    handler = fastf1.testing.OfflineCacheMissHandler()
    logging.getLogger("fastf1").addHandler(handler)

    Cache.configure(cache_dir=tmpdir, use_requests_cache=False)

    with requests_mock.Mocker() as mocker:
        mocker.get(_PRIMARY_URL, status_code=504)
        mirror = mocker.get(_MIRROR_URL, status_code=504)

        response = Cache.requests_get((_PRIMARY_URL, _MIRROR_URL))

    assert response.status_code == 504
    assert mirror.call_count == 1
    assert handler.missed_urls == set()
