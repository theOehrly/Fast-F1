"""Authentication for requests to livetiming.formula1.com.

Signs in to a Formula 1 account (PingOne identity provider: OAuth2
Authorization-Code + PKCE around a DaVinci username/password widget) and
sends the F1TV subscription token as Bearer token to livetiming.

Modules:
    - ``discovery``: scrapes the OAuth client configuration
    - ``davinci``: the username/password step
    - ``login``: the OAuth flow and the credential source
    - ``tokens``: token, file storage and access
    - ``transport``: the requests adapter that attaches the token

Two sign-in methods are available:

    - ``"password"`` (default): the native sign-in above. Credentials are
      read from the environment variables ``F1_USERNAME`` and
      ``F1_PASSWORD``. If they are not set and the session is interactive,
      the user is prompted for them.
    - ``"browser"``: the legacy sign-in through f1login.fastf1.dev and a
      browser addon (see :mod:`fastf1.internals.f1auth`).

The method is selected with :func:`set_auth_method`, else with the
environment variable ``FASTF1_AUTH_METHOD``. Both methods yield the same
token, which is stored and reused independent of the method.
"""

import os
from collections.abc import Callable

from fastf1.internals.f1account.login import (
    Credentials,
    login
)
from fastf1.internals.f1account.tokens import (
    SubscriptionToken,
    TokenManager,
    TokenStore
)
from fastf1.internals.f1account.transport import (
    LIVETIMING_URL,
    LivetimingAuthAdapter
)


__all__ = [
    "AUTH_METHODS",
    "LIVETIMING_URL",
    "LivetimingAuthAdapter",
    "SubscriptionToken",
    "TokenStore",
    "clear_token",
    "get_auth_method",
    "get_token",
    "set_auth_method",
    "token_manager",
]


AUTH_METHODS = ("password", "browser")
ENV_AUTH_METHOD = "FASTF1_AUTH_METHOD"

_auth_method: str | None = None


def set_auth_method(method: str | None):
    """Select the sign-in method, ``"password"`` or ``"browser"``.

    This takes precedence over the environment variable
    ``FASTF1_AUTH_METHOD``. Pass ``None`` to reset the selection.
    """
    global _auth_method
    _auth_method = method if method is None else _validate_auth_method(method)


def get_auth_method() -> str:
    """Return the selected sign-in method."""
    return _validate_auth_method(_auth_method
                                 or os.environ.get(ENV_AUTH_METHOD)
                                 or AUTH_METHODS[0])


def _validate_auth_method(method: str) -> str:
    if method not in AUTH_METHODS:
        raise ValueError(f"Invalid sign-in method {method!r}, must be one "
                         f"of {', '.join(AUTH_METHODS)}.")
    return method


def _get_authenticator(method: str) -> Callable[[], SubscriptionToken]:
    if _validate_auth_method(method) == "browser":
        # imported here, f1auth itself imports from this package
        from fastf1.internals.f1auth import login_browser
        return login_browser
    return lambda: login(Credentials.from_env_or_prompt())


token_manager = TokenManager(
    TokenStore.default(),
    authenticate=lambda: _get_authenticator(get_auth_method())(),
)


def get_token(
        force_renew: bool = False, method: str | None = None
) -> SubscriptionToken:
    """Return a valid livetiming token, signing in if necessary.

    Args:
        force_renew: sign in even if a valid token exists
        method: sign in with this method instead of the selected one
    """
    authenticate = _get_authenticator(method) if method else None
    return token_manager.get(force_renew, authenticate)


def clear_token():
    """Remove the stored livetiming token from memory and disk."""
    token_manager.clear()
