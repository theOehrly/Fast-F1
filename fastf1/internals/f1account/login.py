"""OAuth2 Authorization-Code + PKCE sign-in to the Formula 1 account.

The identity provider (PingOne) runs the username/password step as a
DaVinci flow. With PingOne's redirectless ``response_mode=pi.flow``, every
step is a JSON API call instead of an HTML page:

    1. Discover the client configuration (see ``discovery``).
    2. GET  /as/authorize -> JSON describing the login form and the url to
                             submit it to
    3. POST <next url>    -> submits username + password, returns the
                             authorization code
    4. POST /as/token     -> exchange the code for the access token.

No refresh token is issued; once the token expires, the sign-in is repeated.
"""

import base64
import getpass
import hashlib
import os
import secrets
import sys

import jwt
import requests

from fastf1.exceptions import F1AuthError
from fastf1.internals.f1account.common import (
    AUTHORIZE_URL,
    DEFAULT_HEADERS,
    IDP_ORIGIN,
    TIMEOUT,
    TOKEN_URL,
    logger
)
from fastf1.internals.f1account.discovery import (
    AuthConfig,
    fetch_config
)
from fastf1.internals.f1account.tokens import SubscriptionToken


ENV_USERNAME = "F1_USERNAME"
ENV_PASSWORD = "F1_PASSWORD"

# requests JSON instead of HTML responses from the DaVinci flow
PING_SDK_HEADERS = {"X-Requested-With": "ping-sdk"}


def default_login() -> SubscriptionToken:
    """Sign in with the credentials from the environment or a prompt."""
    return login(*_credentials_from_env_or_prompt())


def login(username: str, password: str) -> SubscriptionToken:
    """Sign in and return the subscription token for the F1 APIs.

    Raises ``F1AuthError`` on any failure.
    """
    # attempt to get a current browser user agent, else the hard-coded
    # default chrome UA is used
    if ua := _get_current_user_agent():
        DEFAULT_HEADERS.update({"User-Agent": ua})

    try:
        # the IdP ties the steps of the flow together through cookies, so
        # every step must share this session
        with requests.Session() as session:
            session.headers.update(DEFAULT_HEADERS)
            config = fetch_config(session)
            access_token = _do_login_flow(session, config, username, password)
    except requests.RequestException as exc:
        raise F1AuthError(f"Sign-in failed: {exc}") from exc

    # extract the subscription token from the claims that are carried by the
    # access token
    try:
        claims = jwt.decode(access_token, options={"verify_signature": False})
    except jwt.PyJWTError as exc:
        raise F1AuthError("Failed to decode the access token.") from exc
    if not (value := claims.get("subscriptionToken")):
        raise F1AuthError("Access token contains no subscription token. "
                          "An active F1TV subscription is required.")
    return SubscriptionToken.from_jwt(value)


def _get_current_user_agent() -> str | None:
    from fastf1.req import Cache
    try:
        resp = Cache.requests_get(
            "https://jnrbsn.github.io/user-agents/user-agents.json",
            timeout=TIMEOUT
        )
        resp.raise_for_status()
        ua = resp.json()[0]
    except (requests.RequestException, ValueError, LookupError, TypeError):
        logger.warning("Failed to update user agent for login.")
        return None
    return ua if isinstance(ua, str) and ua else None


def _do_login_flow(
        session: requests.Session,
        config: AuthConfig,
        username: str,
        password: str
) -> str:
    """Run the OAuth flow and return the access token."""
    code_verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(24)

    resp = session.get(
        AUTHORIZE_URL,
        params={
            "client_id": config.client_id,
            "response_type": "code",
            "response_mode": "pi.flow",
            # the subscription token is included with any scope
            "scope": "openid",
            "state": state,
            "nonce": secrets.token_urlsafe(24),
            "code_challenge": _code_challenge(code_verifier),
            "code_challenge_method": "S256",
            # selects the DaVinci flow
            "acr_values": config.policy_id,
        },
        headers=PING_SDK_HEADERS,
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    form = resp.json()
    try:
        submit_url = form["_links"]["next"]["href"]
        interaction_id = form["interactionId"]
        flow_id = form["id"]
        event_name = form["eventName"]
    except (KeyError, TypeError) as exc:
        raise F1AuthError(
            "Unexpected response when starting the sign-in.") from exc
    if not submit_url.startswith(f"{IDP_ORIGIN}/"):
        # never send the credentials anywhere else
        raise F1AuthError(f"Unexpected sign-in url {submit_url}.")

    resp = session.post(
        submit_url,
        json={
            "id": flow_id,
            "eventName": event_name,
            "interactionId": interaction_id,
            "parameters": {
                "eventType": "submit",
                "data": {
                    "actionKey": "SIGNIN",
                    "formData": {"username": username, "password": password},
                },
            },
        },
        headers={**PING_SDK_HEADERS, "interactionId": interaction_id},
        timeout=TIMEOUT,
    )
    code = _code_from_flow_response(resp, state)

    resp = session.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": config.client_id,
            "code": code,
            "code_verifier": code_verifier,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    try:
        return resp.json()["access_token"]
    except (ValueError, KeyError, TypeError) as exc:
        raise F1AuthError("No access token in the token response.") from exc


def _code_challenge(code_verifier: str) -> str:
    """PKCE S256 code challenge (RFC 7636)."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _code_from_flow_response(resp: requests.Response, state: str) -> str:
    """Return the authorization code from the final DaVinci response."""
    try:
        data = resp.json()
    except ValueError:
        resp.raise_for_status()
        raise F1AuthError("Unexpected response from the sign-in.") from None

    if data.get("status") != "COMPLETED":
        # e.g. wrong credentials; the message is meant for the user
        raise F1AuthError(data.get("message")
                          or f"Sign-in failed (status {resp.status_code}).")
    auth_response = data.get("authorizeResponse") or {}
    if auth_response.get("state") != state:
        raise F1AuthError("Sign-in failed: state mismatch in the response.")
    if not ((code := auth_response.get("code")) and isinstance(code, str)):
        raise F1AuthError("Sign-in failed: no authorization code returned.")
    return code


def _credentials_from_env_or_prompt() -> tuple[str, str]:
    """Read the credentials from the environment variables ``F1_USERNAME``
    and ``F1_PASSWORD``, or prompt for missing values if the session is
    interactive."""
    username = os.environ.get(ENV_USERNAME)
    password = os.environ.get(ENV_PASSWORD)
    if username and password:
        return username, password

    if not sys.stdin.isatty():
        raise F1AuthError(
            f"No F1 account credentials available. Set the environment "
            f"variables {ENV_USERNAME} and {ENV_PASSWORD}.")
    try:
        username = username or input("F1 account email: ")
        password = password or getpass.getpass("F1 account password: ")
    except EOFError as exc:
        raise F1AuthError("No F1 account credentials entered.") from exc
    return username, password
