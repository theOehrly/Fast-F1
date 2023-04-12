import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--no-f1-tel-api", action="store_true", default=False,
        help="skip tests which require connecting to the f1 telemetry api"
    )
    parser.addoption(
        "--ergast-api", action="store_true", default=False,
        help="run tests which require connecting to ergast"
    )
    parser.addoption(
        "--lint-only", action="store_true", default=False,
        help="only run linter and skip all tests"
    )
    parser.addoption(
        "--prj-doc", action="store_true", default=False,
        help="run only tests for general project structure and documentation"
    )
    parser.addoption(
        "--slow", action="store_true", default=False,
        help="run very slow tests too: this may take 30 minutes or more and will may multiple"
             "hundred requests to the api server - usage is highly discouraged"
    )


def pytest_configure(config):
    config.addinivalue_line("markers", "f1telapi: test connects to the f1 telemetry api")
    config.addinivalue_line("markers", "ergastapi: test connects to the ergast api")
    config.addinivalue_line("markers", "prjdoc: general non-code tests for project and structure")
    config.addinivalue_line("markers", "slow: extremely slow tests (multiple minutes)")


def pytest_collection_modifyitems(config, items):
    # cli conditional skip extremely slow tests
    if not config.getoption("--slow"):
        skip_slow = pytest.mark.skip(reason="need --slow option to run; usage highly discouraged")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    # cli conditional skip test that use the cache or connect to the
    # f1 api directly
    if config.getoption("--no-f1-tel-api"):
        skip_f1_tel = pytest.mark.skip(reason="--no-f1-tel-api set")
        for item in items:
            if "f1telapi" in item.keywords:
                item.add_marker(skip_f1_tel)

    # cli conditional skip test that connect to the ergast api
    if not config.getoption("--ergast-api"):
        skip_ergast = pytest.mark.skip(reason="need --ergast-api option to run")
        for item in items:
            if "ergastapi" in item.keywords:
                item.add_marker(skip_ergast)

    # lint only: skip all
    if config.getoption('--lint-only'):
        items[:] = [item for item in items if item.get_closest_marker('flake8')]

    # only test documentation and project structure
    if config.getoption('--prj-doc'):
        skip_non_prj = pytest.mark.skip(reason="--prj-doc given: run only project structure and documentation tests")
        for item in items:
            if "prjdoc" not in item.keywords:
                item.add_marker(skip_non_prj)
    else:
        skip_prj = pytest.mark.skip(reason="need --prj-doc to run project structure and documentation tests")
        for item in items:
            if "prjdoc" in item.keywords:
                item.add_marker(skip_prj)


@pytest.fixture
def reference_laps_data():
    # provides a reference instance of session and laps to tests which
    # require it
    import fastf1
    fastf1.Cache.enable_cache("test_cache/")
    session = fastf1.get_session(2020, 'Italy', 'R')
    session.load()
    return session, session.laps


@pytest.fixture(autouse=True)
def fastf1_setup():
    import fastf1
    from fastf1.logger import LoggingManager
    fastf1.Cache.enable_cache('test_cache')  # use specific cache directory
    fastf1.Cache.ci_mode(True)  # only request uncached data
    LoggingManager.debug = True  # raise all exceptions
