"""OAuth2 Authorization-Code + PKCE sign-in to the Formula 1 account.

    1. Discover the client configuration (see ``discovery``).
    2. GET  /as/authorize -> login page; sets the IdP session cookies and
                             embeds the DaVinci SDK token.
    3. DaVinci username/password step (see ``davinci``) -> ``dvResponse``.
    4. POST /as/resume    -> redirect to the redirect uri with ?code=...
    5. POST /as/token     -> exchange the code for the access token.

PKCE, the ``state`` check and error handling of the OAuth parts are done by
requests-oauthlib. No refresh token is issued; once the token expires, the
sign-in is repeated.
"""

import getpass
import os
import secrets
import sys
from dataclasses import (
    dataclass,
    field
)

import requests
from oauthlib.oauth2 import OAuth2Error
from requests_oauthlib import OAuth2Session

from fastf1.exceptions import F1AuthError
from fastf1.internals.f1account import davinci
from fastf1.internals.f1account.common import (
    ACCOUNT_ORIGIN,
    AUTHORIZE_URL,
    DEFAULT_HEADERS,
    IDP_ORIGIN,
    RESUME_URL,
    TIMEOUT,
    TOKEN_URL
)
from fastf1.internals.f1account.discovery import (
    AuthConfig,
    fetch_config
)
from fastf1.internals.f1account.tokens import SubscriptionToken


ENV_USERNAME = "F1_USERNAME"
ENV_PASSWORD = "F1_PASSWORD"


@dataclass(frozen=True)
class Credentials:
    username: str
    password: str = field(repr=False)

    @classmethod
    def from_env_or_prompt(cls) -> "Credentials":
        """Read the credentials from the environment variables
        ``F1_USERNAME`` and ``F1_PASSWORD``, or prompt for missing values if
        the session is interactive."""
        username = os.environ.get(ENV_USERNAME)
        password = os.environ.get(ENV_PASSWORD)
        if username and password:
            return cls(username, password)

        if not sys.stdin.isatty():
            raise F1AuthError(
                f"No F1 account credentials available. Set the environment "
                f"variables {ENV_USERNAME} and {ENV_PASSWORD}.")
        try:
            username = username or input("F1 account email: ")
            password = password or getpass.getpass("F1 account password: ")
        except EOFError as exc:
            raise F1AuthError("No F1 account credentials entered.") from exc
        return cls(username, password)


def login(credentials: Credentials) -> SubscriptionToken:
    """Sign in and return the livetiming token.

    Raises ``F1AuthError`` on any failure.
    """
    try:
        with requests.Session() as session:
            session.headers.update(DEFAULT_HEADERS)
            config = fetch_config(session)
        return _login(config, credentials)
    except (requests.RequestException, OAuth2Error) as exc:
        raise F1AuthError(f"Sign-in failed: {exc}") from exc


def _login(config: AuthConfig, credentials: Credentials) -> SubscriptionToken:
    # One session = one cookie jar. The cookies set by the authorize request
    # let /as/resume map the DaVinci result back onto the OAuth request, so
    # every step must share this session.
    with OAuth2Session(config.client_id, redirect_uri=config.redirect_uri,
                       scope=config.scope, pkce="S256") as oauth:
        oauth.headers.update(DEFAULT_HEADERS)

        url, _state = oauth.authorization_url(
            AUTHORIZE_URL,
            nonce=secrets.token_urlsafe(24),
            acr_values=config.policy_id,
            journey="login",
            ch="COWB",
            language="en",
        )
        resp = oauth.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
        page = davinci.LoginPage.parse(url, resp.text)

        dv_response = davinci.sign_in(oauth, page, config.policy_id,
                                      credentials.username,
                                      credentials.password)

        # do not follow the redirect, the code is in the Location header
        resp = oauth.post(
            RESUME_URL,
            data={"dvResponse": dv_response, "state": page.resume_state},
            headers={"Origin": IDP_ORIGIN, "Referer": page.url},
            allow_redirects=False,
            timeout=TIMEOUT,
        )
        if not resp.is_redirect:
            raise F1AuthError(f"Resuming the sign-in did not redirect "
                              f"(status {resp.status_code}).")

        # The granted scopes are irrelevant here. Without an expected scope,
        # oauthlib does not raise if the server reports different scopes.
        oauth.scope = None
        token = oauth.fetch_token(
            TOKEN_URL,
            authorization_response=resp.headers["Location"],
            include_client_id=True,
            headers={"Referer": f"{ACCOUNT_ORIGIN}/"},
            timeout=TIMEOUT,
        )

    return SubscriptionToken.from_access_token(token["access_token"],
                                               token.get("expires_at"))
