try:
    from . import _version
except ImportError:
    _version = None

__version__ = getattr(_version, 'version', '0.0+UNKNOWN')
__version_tuple__ = getattr(_version, 'version_tuple', (0, 0, '+UNKNOWN'))
if __version_tuple__:
    # create a short version containing only the public version
    __version_short__ = ".".join(str(digit) for digit in __version_tuple__
                                 if str(digit).isnumeric())
else:
    __version_short__ = __version__


from fastf1.events import get_session  # noqa: F401
from fastf1.events import (  # noqa: F401
    get_event,
    get_event_schedule,
    get_events_remaining,
    get_testing_event,
    get_testing_session
)
from fastf1.logger import set_log_level  # noqa: F401
from fastf1.req import (  # noqa: F401
    Cache,
    RateLimitExceededError
)
