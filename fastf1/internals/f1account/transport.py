"""Transport adapter that authenticates requests to livetiming."""

import requests
from requests.adapters import HTTPAdapter

from fastf1.exceptions import F1AuthError
from fastf1.internals.f1account.tokens import (
    SubscriptionToken,
    TokenManager
)
from fastf1.logger import get_logger


_logger = get_logger(__name__)

# mount the adapter on this prefix only; no other host ever sees the token
LIVETIMING_URL = "https://livetiming.formula1.com/"


class LivetimingAuthAdapter(HTTPAdapter):
    """Adds the Bearer token to every request that it sends.

    As a transport adapter, it is only used for requests that are actually
    sent over the network. Responses served from the cache or in offline
    mode never trigger a sign-in.

    If no token can be obtained, a warning is logged and the request is sent
    without authentication. If the server rejects the token, it is
    discarded and the request is retried once with a new token.
    """

    def __init__(self, tokens: TokenManager, **kwargs):
        super().__init__(**kwargs)
        self._tokens = tokens

    def send(self, request: requests.PreparedRequest, **kwargs
             ) -> requests.Response:
        token = self._get_token()
        resp = super().send(_with_token(request, token), **kwargs)

        if resp.status_code == 401 and token is not None:
            # the token may have been revoked before its expiry time
            _logger.warning("Access token was rejected by the server. "
                            "Signing in again.")
            self._tokens.clear()
            if (token := self._get_token()) is not None:
                resp.close()
                resp = super().send(_with_token(request, token), **kwargs)

        return resp

    def _get_token(self) -> SubscriptionToken | None:
        try:
            return self._tokens.get()
        except F1AuthError as exc:
            _logger.warning(f"Failed to authenticate with Formula 1 account, "
                            f"continuing without authentication: {exc}")
            return None


def _with_token(
        request: requests.PreparedRequest, token: SubscriptionToken | None
) -> requests.PreparedRequest:
    if token is None:
        return request
    # copy, so that the token is not added to the caller's request object
    request = request.copy()
    request.headers["Authorization"] = token.authorization_header
    return request
