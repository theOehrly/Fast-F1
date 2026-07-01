import logging
import os
import re

import pytest

import fastf1.testing


ERGAST_BACKEND_OVERRIDE = os.environ.get("FASTF1_TEST_ERGAST_BACKEND_OVERRIDE")

if ERGAST_BACKEND_OVERRIDE:
    import fastf1.ergast

    fastf1.ergast.interface.BASE_URL = ERGAST_BACKEND_OVERRIDE


# URLs for which no frozen test data exists, collected during the test run
OFFLINE_CACHE_MISSES: set[str] = set()


class _OfflineCacheMissHandler(logging.Handler):
    """Collects the URLs that FastF1 could not serve from the frozen test
    data, so that they can be reported once at the end of the test run."""
    _PATTERN = re.compile(r"^Offline mode is enabled but no cached response "
                          r"is available for '(?P<url>.*)'$")

    def emit(self, record):
        match = self._PATTERN.match(record.getMessage())
        if match is not None:
            OFFLINE_CACHE_MISSES.add(match["url"])


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
        "--prj-doc", action="store_true", default=False,
        help="run only tests for general project structure and documentation"
    )
    parser.addoption(
        "--slow", action="store_true", default=False,
        help="run very slow tests too: this may take 30 minutes or more and "
             "will make multiple hundred requests to the api server - usage "
             "is highly discouraged"
    )

    parser.addoption(
        "--create-http-cache", action="store_true", default=False,
        help="Create the HTTP cache or update it if it already exists. "
             "Expired/unused responses will be deleted."
    )


def pytest_configure(config):
    config.addinivalue_line("markers",
                            "f1telapi: test connects to the f1 telemetry api")
    config.addinivalue_line("markers",
                            "ergastapi: test connects to the ergast api")
    config.addinivalue_line("markers",
                            "prjdoc: general non-code tests for project and "
                            "structure")
    config.addinivalue_line("markers",
                            "slow: extremely slow tests (multiple minutes)")

    if config.getoption("--create-http-cache"):
        if config.getoption("dist", "no") != "no":
            raise RuntimeError(
                "--create-http-cache must not be run with xdist"
            )
        fastf1.testing.CREATE_HTTP_CACHE = True

    fastf1.testing.enable_test_cache()

    # Collect missing test data, so that it can be reported in the terminal
    # summary with an actionable message.
    logging.getLogger("fastf1").addHandler(_OfflineCacheMissHandler())

    # Delete cached function output (stage 2), so that all http requests
    # access the Cache to renew the entries if necessary. The HTTP cache
    # itself is not deleted!
    from fastf1 import Cache
    Cache.clear_cache()


def pytest_collection_modifyitems(config, items):
    # cli conditional skip extremely slow tests
    if not config.getoption("--slow"):
        skip_slow = pytest.mark.skip(reason="need --slow option to run; "
                                            "usage highly discouraged")
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
        skip_ergast = pytest.mark.skip(reason="need --ergast-api option to "
                                              "run")
        for item in items:
            if "ergastapi" in item.keywords:
                item.add_marker(skip_ergast)

    # only test documentation and project structure
    if config.getoption("--prj-doc"):
        skip_non_prj = pytest.mark.skip(reason="--prj-doc given: run only "
                                               "project structure and "
                                               "documentation tests")
        for item in items:
            if "prjdoc" not in item.keywords:
                item.add_marker(skip_non_prj)
    else:
        skip_prj = pytest.mark.skip(reason="need --prj-doc to run project "
                                           "structure and documentation tests")
        for item in items:
            if "prjdoc" in item.keywords:
                item.add_marker(skip_prj)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    terminalreporter.ensure_newline()
    terminalreporter.section("Parameter Overrides", sep="-", blue=True,
                             bold=True)
    terminalreporter.line(f"Ergast backend override: "
                          f"{ERGAST_BACKEND_OVERRIDE}")

    if config.getoption("--create-http-cache"):
        _report_recorded_data(terminalreporter)
    elif exitstatus and OFFLINE_CACHE_MISSES:
        # Only report on failure. Some requests are expected to miss, for
        # example when the primary API is unavailable and the test data was
        # recorded from the mirror instead.
        _report_missing_data(terminalreporter)


def _report_missing_data(terminalreporter):
    terminalreporter.ensure_newline()
    terminalreporter.section("Missing Test Data", sep="-", red=True, bold=True)
    terminalreporter.line(
        "The tests run offline against frozen test data. No data is "
        "available for the following requests:"
    )
    for url in sorted(OFFLINE_CACHE_MISSES):
        terminalreporter.line(f"  {url}")
    terminalreporter.line(
        "\nIf this is caused by an outdated submodule, run "
        "`git submodule update --init --depth 1` to get the latest test "
        "dataset."
        "\nIf a test requires new data, record it with "
        "`python -m pytest --create-http-cache <test>` and contribute "
        "the new files in fastf1/testing/data/ to "
        "https://github.com/theOehrly/fastf1-test-data."
        "\nMissing cached requests may be irrelevant for some tests if "
        "test data is fetched from a fallback mirror instead."
    )


def _report_recorded_data(terminalreporter):
    import subprocess

    # the submodule's working tree; git reports paths relative to it
    submodule_dir = os.path.dirname(fastf1.testing.HTTP_CACHE_DIR)

    proc = subprocess.run(
        ["git", "-C", submodule_dir,
         "status", "--porcelain", "--untracked-files=all"],
        capture_output=True, text=True, check=False
    )
    if proc.returncode:
        return

    # porcelain format: two status characters, a space, then the path
    files = [line[3:] for line in proc.stdout.splitlines()]

    terminalreporter.ensure_newline()
    terminalreporter.section("Recorded Test Data", sep="-", blue=True,
                             bold=True)
    if not files:
        terminalreporter.line("No new test data was recorded.")
        return

    total = 0
    for name in sorted(files):
        terminalreporter.line(f"  {name}")
        total += os.path.getsize(os.path.join(submodule_dir, name))

    terminalreporter.line(
        f"\n{len(files)} file(s), {total / 1024 ** 2:.1f} MB. Commit these in "
        f"fastf1/testing/data/ and contribute them to "
        f"https://github.com/theOehrly/fastf1-test-data"
    )


@pytest.fixture
def reference_laps_data():
    # provides a reference instance of session and laps to tests which
    # require it
    import fastf1
    session = fastf1.get_session(2020, "Italy", "R")
    session.load()
    return session, session.laps


@pytest.fixture(autouse=True)
def fastf1_setup():
    from fastf1.logger import LoggingManager

    fastf1.testing.enable_test_cache()

    LoggingManager.debug = True  # raise all exceptions


@pytest.fixture(autouse=True)
def automock_terminal_size(doctest_namespace):  # noqa: ARG001
    # Patching inside an autouse=True fixture ensures that it is applied to
    # all tests but not to the pytest result output in the terminal.
    # Requiring the doctest_namespace fixture ensures that the patch also
    # applies to doctests.
    fastf1.testing.enable_terminal_size_mock()
