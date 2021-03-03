import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--f1-tel-api", action="store_true", default=False,
        help="run tests which require connecting to the f1 telemetry api"
    )
    parser.addoption(
        "--ergast-api", action="store_true", default=False,
        help="run tests which require connecting to ergast"
    )
    parser.addoption(
        "--lint-only", action="store_true", default=False,
        help="only run linter and skip all tests"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "f1telapi: test connects to the f1 telemetry api")
    config.addinivalue_line("markers", "ergastapi: test connects to the ergast api")


def pytest_collection_modifyitems(config, items):
    # cli conditional skip test that connect to the f1 telemetry api
    if config.getoption("--f1-tel-api"):
        # --f1-tel-api given in cli: do not skip slow tests
        return
    else:
        skip_f1_tel = pytest.mark.skip(reason="need --f1-tel-api option to run")
        for item in items:
            if "f1telapi" in item.keywords:
                item.add_marker(skip_f1_tel)

    # cli conditional skip test that connect to the ergast api
    if config.getoption("--ergast-api"):
        # --ergast-api given in cli: do not skip slow tests
        return
    else:
        skip_ergast = pytest.mark.skip(reason="need --ergast-api option to run")
        for item in items:
            if "ergastapi" in item.keywords:
                item.add_marker(skip_ergast)

    if config.getoption('--lint-only'):
        items[:] = [item for item in items if item.get_closest_marker('flake8')]


@pytest.fixture
def reference_laps_data():
    # provides a reference instance of session and laps to tests which
    # require it
    import fastf1
    fastf1.Cache.enable_cache("test_cache/")
    session = fastf1.get_session(2020, 'Italy', 'R')
    laps = session.load_laps()
    return session, laps
