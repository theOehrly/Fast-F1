import fastf1.ergast.interface

# imports for exposed names
from fastf1.ergast.interface import Ergast  # noqa: F401
from fastf1.ergast.legacy import \
    fetch_day, \
    fetch_season, \
    fetch_results  # noqa: F401


@property
def base_url():
    # TODO warn
    return fastf1.ergast.interface.BASE_URL
