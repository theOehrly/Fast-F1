"""Discovery of the OAuth client configuration.

The endpoint urls are fixed, but the client id, DaVinci policy id, scope and
redirect uri are app settings that F1 may change at any time. They are read
from the public ``davinci:{...}`` config object of the account.formula1.com
frontend, so that changed values are picked up without a FastF1 release.
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

_JS_STRING = r'"((?:[^"\\]|\\.)*)"'
_BRACE_OR_STRING = re.compile(r'"(?:[^"\\]|\\.)*"|[{}]')


@dataclass(frozen=True)
class AuthConfig:
    client_id: str
    # acr_values in the authorize request == the DaVinci policy id
    policy_id: str
    scope: str
    # must match byte-for-byte at the token endpoint, fragment included
    redirect_uri: str


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
    body = _object_literal(script, r"\bdavinci:\s*\{")

    def string_field(name: str) -> str | None:
        m = re.search(rf"\b{name}:\s*{_JS_STRING}", body)
        return m.group(1) if m else None

    # redirectUri is a JS expression: window.location.origin + "<suffix>"
    redirect_m = re.search(
        rf"\bredirectUri:\s*window\.location\.origin\s*\+\s*{_JS_STRING}",
        body
    )

    fields = {
        "clientId": string_field("clientId"),
        # registrationAcrValues is a fallback for the policy id
        "acrValues": (string_field("acrValues")
                      or string_field("registrationAcrValues")),
        "scope": string_field("scope"),
        "redirectUri": (ACCOUNT_ORIGIN + redirect_m.group(1)
                        if redirect_m else None),
    }
    if missing := [name for name, value in fields.items() if not value]:
        raise F1AuthError(f"Config scrape missing required field(s): "
                          f"{', '.join(missing)}")

    return AuthConfig(
        client_id=fields["clientId"],
        policy_id=fields["acrValues"],
        scope=fields["scope"],
        redirect_uri=fields["redirectUri"],
    )


def _object_literal(script: str, opening: str) -> str:
    """Return the body of the JS object literal that starts with the regex
    ``opening`` (which must end with the opening brace).

    Nested objects are kept and braces inside string literals are ignored.
    """
    if not (m := re.search(opening, script)):
        raise F1AuthError(f"No config object found in {CONFIG_SCRIPT_URL}")
    depth = 1
    for token in _BRACE_OR_STRING.finditer(script, m.end()):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return script[m.end():token.start()]
    raise F1AuthError(f"Unbalanced config object in {CONFIG_SCRIPT_URL}")
