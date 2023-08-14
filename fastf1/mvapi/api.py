import requests.exceptions

from typing import Optional

from fastf1.mvapi.internals import _logger
from fastf1.req import Cache
from fastf1.version import __version__


PROTO = "https"
HOST = "api.multiviewer.app"
HEADERS = {'User-Agent': f'FastF1/{__version__}'}


def _make_url(path: str):
    return f"{PROTO}://{HOST}{path}"


def get_circuit(*, year: int, circuit_key: int) -> Optional[dict]:
    """:meta private:
    Request circuit data from the MultiViewer API and return the JSON
    response."""
    url = _make_url(f"/api/v1/circuits/{circuit_key}/{year}")
    response = Cache.requests_get(url, headers=HEADERS)
    if response.status_code != 200:
        _logger.debug(f"[{response.status_code}] {response.content.decode()}")
        return None

    try:
        return response.json()
    except requests.exceptions.JSONDecodeError:
        return None
