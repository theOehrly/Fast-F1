import fastf1
import os


def test_enable_cache(tmpdir):
    fastf1.Cache.enable_cache(tmpdir)


def test_cache_used_and_clear(tmpdir):
    fastf1.Cache.enable_cache(tmpdir)

    session = fastf1.get_session(2020, 5, 'FP2')  # rainy and short session, good for fast test/quick loading
    session.load_laps()

    cache_dir_path = os.path.join(tmpdir, session.api_path[8:])

    # pickled result should now exist
    assert os.listdir(cache_dir_path) == ['car_data.ff1pkl',
                                          'position_data.ff1pkl',
                                          'timing_app_data.ff1pkl',
                                          'timing_data.ff1pkl',
                                          'track_status_data.ff1pkl']

    # requests cache should exist and should be used (size larger than 10Mb)
    assert os.path.getsize(os.path.join(tmpdir, 'fastf1_http_cache.sqlite')) > 10e6

    fastf1.Cache.clear_cache(tmpdir)  # should delete pickle files
    assert os.listdir(cache_dir_path) == []

    fastf1.Cache.clear_cache(tmpdir, deep=True)  # should clear requests http cache
    assert os.path.getsize(os.path.join(tmpdir, 'fastf1_http_cache.sqlite')) < 50000  # 100kB
