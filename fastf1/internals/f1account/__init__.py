"""Authentication for requests to livetiming.formula1.com.

Signs in to a Formula 1 account (PingOne identity provider: OAuth2
Authorization-Code + PKCE around a DaVinci username/password flow) and
sends the F1TV subscription token as Bearer token to livetiming.

Modules:
    - ``discovery``: scrapes the OAuth client configuration
    - ``login``: the native sign-in and the credential source
    - ``browser``: the legacy browser sign-in
    - ``tokens``: token, file storage and access
    - ``transport``: the requests adapter that attaches the token

Two sign-in methods are available:

    - ``"password"`` (default): the native sign-in above. Credentials are
      read from the environment variables ``F1_USERNAME`` and
      ``F1_PASSWORD``. If they are not set and the session is interactive,
      the user is prompted for them.
    - ``"browser"``: the legacy sign-in through f1login.fastf1.dev and a
      browser addon (see :mod:`fastf1.internals.f1account.browser`).

The method is selected with :func:`set_auth_method`, else with the
environment variable ``FASTF1_AUTH_METHOD``. Both methods yield the same
token, which is stored and reused independent of the method.
"""

import os

from fastf1.internals.f1account.browser import login_browser
from fastf1.internals.f1account.login import default_login
from fastf1.internals.f1account.tokens import (
    SubscriptionToken,
    TokenManager
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
    "clear_token",
    "get_auth_method",
    "get_token",
    "set_auth_method",
    "token_manager",
]


_AUTHENTICATORS = {
    "password": default_login,
    "browser": login_browser,
}

AUTH_METHODS = tuple(_AUTHENTICATORS)
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


def _authenticate() -> SubscriptionToken:
    # get and call the currently set authenticator
    return _AUTHENTICATORS[get_auth_method()]()


token_manager = TokenManager(auth_func=_authenticate)


def get_token(
        force_renew: bool = False, method: str | None = None
) -> SubscriptionToken:
    """Return a valid livetiming token, signing in if necessary.

    Args:
        force_renew: sign in even if a valid token exists
        method: sign in with this method instead of the selected one
    """
    authenticate = (_AUTHENTICATORS[_validate_auth_method(method)]
                    if method else None)
    return token_manager.get(force_renew, authenticate)


def clear_token():
    """Remove the stored livetiming token from memory and disk."""
    token_manager.clear()
