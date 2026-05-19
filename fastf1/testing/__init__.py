"""Collection of functions to simplify tests.
"""

import io
import logging
import multiprocessing
from typing import Callable


_MP_CONFIGURED = False


class SubprocessTestError(Exception):
    """Raised if an Exception is encountered in a subprocess test.
    """
    pass


class AllStatusCodes(tuple):
    def __contains__(self, item):
        return True


def subprocess_wrapper(*func_args,
                       __func,
                       __use_default_cache,
                       __mock_terminal_size,
                       __raise_soft_exceptions,
                       __patch_cache_error_responses,
                       **func_kwargs):
    if __use_default_cache:
        enable_test_cache()
    if __mock_terminal_size:
        enable_terminal_size_mock()
    if __raise_soft_exceptions:
        from fastf1.logger import LoggingManager
        LoggingManager.debug = True  # raise all exceptions
    if __patch_cache_error_responses:
        from fastf1 import Cache
        cache_settings = Cache._requests_session_cached.settings

        # cache expected error response so that tests can be run offline
        cache_settings.allowable_codes = AllStatusCodes()
        cache_settings.cache_control = False

    __func(*func_args, **func_kwargs)


def run_in_subprocess(
        func: Callable,
        *args,
        use_default_cache: bool = True,
        raise_soft_exceptions: bool = True,
        mock_terminal_size: bool = True,
        patch_cache_error_responses: bool = False,
        **kwargs):
    """Runs a function in a subprocess.

    Args:
        func (callable): The test function that is run
        *args (any): passed on to func
        use_default_cache (bool, optional): Configure the default cache
            equivalently to non-subprocess tests.
        raise_soft_exceptions (bool, optional): Raise soft exceptions
            equivalently to non-subprocess tests.
        mock_terminal_size (bool, optional): Configure the terminal size mock
            equivalently to non-subprocess tests.
        patch_cache_error_responses (bool, optional): Patches the default cache
            to also cache error responses. Requires ``use_default_cache=True``.
        **kwargs (any) passed on to func

    Raises:
        SubprocessTestError: The subprocess finished with a non-zero exitcode
    """
    if patch_cache_error_responses and not use_default_cache:
        raise ValueError("Argument `patch_cache_error_responses` requires "
                         "`use_default_cache=True`")

    global _MP_CONFIGURED
    if not _MP_CONFIGURED:
        multiprocessing.set_start_method('spawn')
        # "spawn" is slower than the linux default but ensure that the child
        # process is created cleanly with no inherited state in all cases
        _MP_CONFIGURED = True

    # inject internal arguments for wrapper configuration
    kwargs.update({
        '__func': func,
        '__use_default_cache': use_default_cache,
        '__mock_terminal_size': mock_terminal_size,
        '__raise_soft_exceptions': raise_soft_exceptions,
        '__patch_cache_error_responses': patch_cache_error_responses
    })

    prcs = multiprocessing.Process(
        target=subprocess_wrapper, args=args, kwargs=kwargs
    )
    prcs.start()
    prcs.join()
    if prcs.exitcode != 0:
        raise SubprocessTestError


class LogOutputHandle:
    """A handle to access captured log output.

    Used by :func:`capture_log`

    Args:
        stream_handler: An instance of :class:`logging.StreamHandler` that
            captures the logging output.
        stream: An instance of :class:`io.StreamIO` that is used as stream
            target by the stream handler.
    """
    def __init__(self, stream_handler, stream):
        self.stream_handler = stream_handler
        self.stream = stream

    @property
    def text(self):
        """Property for accessing the captured logging output as string.
        """
        self.stream_handler.flush()
        return self.stream.getvalue()


def capture_log(level=logging.INFO):
    """Capture logging output during a test run.

    This can be used as an alternative to pytest's ``caplog`` fixture. This is
    for example necessary in subprocess tests, as the ``caplog`` fixture can't
    be passed to the subprocess.

    Args:
        level: Log level at which the log is captured

    Returns:
        :class:`LogOutputHandle`
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    stream = io.StringIO()
    for handler in logger.handlers:
        logger.removeHandler(handler)
    stream_handler = logging.StreamHandler(stream=stream)
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    return LogOutputHandle(stream_handler, stream)


def enable_test_cache():
    import os

    import fastf1

    try:
        fastf1.Cache.configure(cache_dir='test_cache')
    except NotADirectoryError:
        # create the test cache and re-enable
        os.mkdir('test_cache')
        fastf1.Cache.configure(cache_dir='test_cache')

    # Ensure that tests make no actual requests and only run with prepared
    # test data for reliability and repeatability.
    fastf1.Cache.offline_mode(True)


def enable_terminal_size_mock():
    # Patch terminal width for pytest output to ensure consistent output for
    # doctests in all environments. This is especially important for the
    # formatting of Pandas DataFrames.
    import shutil
    shutil.get_terminal_size = lambda *_args, **_kwargs: (80, 24)
