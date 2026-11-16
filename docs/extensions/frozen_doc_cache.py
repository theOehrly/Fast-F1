"""Runs the documentation build against the frozen API responses that are
provided by the ``fastf1-doc-data`` submodule at ``docs/data``.

Outside of recording mode the build is fully offline. Every request that
cannot be served from the frozen data is collected and reported as a build
error, so that the documentation is never published from incomplete data.
"""
import logging
import os

from sphinx.application import Sphinx
from sphinx.util import logging as sphinx_logging

import fastf1.testing


# All paths are derived from this file's location, so that the build does not
# depend on the working directory it is started from.
_EXTENSIONS_DIR = os.path.dirname(os.path.abspath(__file__))
_DOCS_DIR = os.path.dirname(_EXTENSIONS_DIR)
_REPO_DIR = os.path.dirname(_DOCS_DIR)

# Frozen HTTP responses, provided by the doc data git submodule
HTTP_CACHE_DIR = os.path.join(_DOCS_DIR, "data", "http_cache")
# Stage 2 cache (``*.ff1pkl``); disposable, not version controlled
DOC_CACHE_DIR = os.path.join(_REPO_DIR, "doc_cache")

# Record responses that are missing from the frozen data from the live APIs
# instead of failing the build; see ``make record-data``
RECORD = bool(os.environ.get("FASTF1_DOCS_CREATE_HTTP_CACHE"))

_logger = sphinx_logging.getLogger(__name__)
_miss_handler = fastf1.testing.OfflineCacheMissHandler()


def enable_doc_cache():
    """Configures FastF1 to read from the frozen documentation data.

    This is called from ``conf.py`` for each of the three ways in which
    example code is executed: the plot directive, doctests and sphinx-gallery.
    """
    fastf1.testing.enable_frozen_http_cache(
        HTTP_CACHE_DIR, DOC_CACHE_DIR, record=RECORD
    )


def _report_recorded_data():
    files, total = fastf1.testing.report_recorded_data_files(
        os.path.dirname(HTTP_CACHE_DIR)
    )
    if not files:
        _logger.info("No new documentation data was recorded.")
        return

    _logger.info("\n".join(f"  {name}" for name in files))
    _logger.info(
        f"{len(files)} file(s), {total / 1024 ** 2:.1f} MB. Commit these in "
        f"docs/data/ and contribute them to "
        f"https://github.com/theOehrly/fastf1-doc-data"
    )


def _report_missing_data():
    urls = "\n".join(f"  {url}"
                     for url in sorted(_miss_handler.missed_urls))
    raise RuntimeError(
        f"The documentation is built offline against frozen API responses. "
        f"No data is available for the following requests:\n{urls}\n"
        f"If this is caused by an outdated submodule, run "
        f"`git submodule update --init --depth 1 docs/data` to get the "
        f"latest dataset.\n"
        f"If an example requires new data, record it with `make record-data` "
        f"and contribute the new files in docs/data/ to "
        f"https://github.com/theOehrly/fastf1-doc-data."
    )


def _build_finished(app, exception):  # noqa: ARG001
    if RECORD:
        _report_recorded_data()
    elif (exception is None) and _miss_handler.missed_urls:
        # Examples that fail on missing data only produce a build warning,
        # so this is what stops a silently degraded build from being
        # published.
        _report_missing_data()


def setup(app: Sphinx):
    logging.getLogger("fastf1").addHandler(_miss_handler)
    try:
        enable_doc_cache()  # fail early if the frozen data is missing
    except RuntimeError as exc:
        # Sphinx reports any exception raised here as an internal error,
        # with a full traceback and a request to file a bug report against
        # Sphinx itself. Exit directly instead; SystemExit passes through
        # Sphinx's exception handling untouched.
        _logger.error(str(exc))
        raise SystemExit(1) from exc
    app.connect("build-finished", _build_finished)
