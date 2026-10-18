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

Credentials are read from the environment variables ``F1_USERNAME`` and
``F1_PASSWORD``. If they are not set and the session is interactive, the user
is prompted for them.
"""

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
    "LIVETIMING_URL",
    "LivetimingAuthAdapter",
    "SubscriptionToken",
    "clear_token",
    "get_token",
    "token_manager",
]


token_manager = TokenManager(
    TokenStore.default(),
    authenticate=lambda: login(Credentials.from_env_or_prompt()),
)


def get_token(force_renew: bool = False) -> SubscriptionToken:
    """Return a valid livetiming token, signing in if necessary."""
    return token_manager.get(force_renew)


def clear_token():
    """Remove the stored livetiming token from memory and disk."""
    token_manager.clear()
