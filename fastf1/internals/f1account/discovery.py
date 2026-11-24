"""Discovery of the OAuth client configuration.

The endpoint urls are fixed, but the client id and DaVinci policy id are app
settings that F1 might change at any time. They are read from the public
``davinci:{...}`` config object of the account.formula1.com frontend, so
that changed values are picked up without a FastF1 release.
"""

import re
from dataclasses import dataclass

import requests

from fastf1.exceptions import F1AuthError
from fastf1.internals.f1account.common import (
    ACCOUNT_ORIGIN,
    TIMEOUT
)


CONFIG_SCRIPT_URL = f"{ACCOUNT_ORIGIN}/scripts/main.min.js"

# the object is flat, i.e. its body contains no braces
_DAVINCI_OBJECT = re.compile(r"\bdavinci:\{([^}]*)\}")


@dataclass(frozen=True)
class AuthConfig:
    client_id: str
    policy_id: str


def fetch_config(session: requests.Session) -> AuthConfig:
    """Scrape the client configuration from the frontend script."""
    resp = session.get(CONFIG_SCRIPT_URL, timeout=TIMEOUT)
    resp.raise_for_status()
    return parse_frontend_config(resp.text)


def parse_frontend_config(script: str) -> AuthConfig:
    """Extract the configuration from the ``davinci:{...}`` object in the
    minified frontend script.

    Raises ``F1AuthError`` if the object or any required field is missing.
    """
    if not (obj := _DAVINCI_OBJECT.search(script)):
        raise F1AuthError(f"No config object found in {CONFIG_SCRIPT_URL}")

    def field(name: str) -> str:
        if not (m := re.search(rf'\b{name}:"([^"]+)"', obj.group(1))):
            raise F1AuthError(f"Config scrape missing required field "
                              f"{name}")
        return m.group(1)

    return AuthConfig(client_id=field("clientId"),
                      policy_id=field("acrValues"))
