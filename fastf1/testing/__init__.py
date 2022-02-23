"""Collection of functions to simplify tests.
"""

import io
import logging
import multiprocessing


class SubprocessTestError(Exception):
    """Raised if an Excpetion is encounterd in a subprocess test.
    """
    pass


def run_in_subprocess(func, *args, **kwargs):
    """Runs a function in a subprocess.

    Args:
        func (callable): The test function that is run
        *args (any): passed on to func
        **kwargs (any) passed on to func

    Raises:
        SubprocessTestError: The subprocess finished with a non-zero exitcode
    """
    prcs = multiprocessing.Process(target=func, args=args, kwargs=kwargs)
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
