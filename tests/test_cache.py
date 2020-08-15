from fastf1 import core, utils
import os


def test_enable_cache(tmpdir):
    utils.enable_cache(tmpdir)


def test_cache_used_and_clear(tmpdir):
    utils.enable_cache(tmpdir)

    session = core.get_session(2020, 3, 'FP2')  # rainy and short session, good for fast test/quick loading
    session.load_laps()

    # requests cache and pickled result should now exist
    assert os.listdir(tmpdir) == ['2020-07-19_Hungarian_Grand_Prix_2020-07-17_Practice_2_laps.pkl',
                                  'fastf1_http_cache.sqlite']

    utils.clear_cache()  # should delete pickle files
    assert os.listdir(tmpdir) == ['fastf1_http_cache.sqlite']

    utils.clear_cache(deep=True)  # should clear requests http cache
    assert os.path.getsize(os.path.join(tmpdir, 'fastf1_http_cache.sqlite')) < 100000  # 100kB
