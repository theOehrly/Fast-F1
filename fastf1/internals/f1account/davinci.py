"""Username/password step through the PingOne DaVinci widget.

The authorize endpoint does not redirect to a classic login form but serves
a page that bootstraps the DaVinci JS SDK. There is no Python SDK for
DaVinci, therefore the requests that the widget sends are reproduced here:

    1. POST /davinci/policy/{policy}/start
                    -> opens a DaVinci interaction
    2. POST /davinci/connections/{conn}/capabilities/customHTMLTemplate
                    -> submits username + password, returns the signed
                       ``dvResponse`` JWT that resumes the OAuth flow
"""

import json
from dataclasses import dataclass
from html.parser import HTMLParser

import requests

from fastf1.exceptions import F1AuthError
from fastf1.internals.f1account.common import (
    DAVINCI_URL,
    IDP_ORIGIN,
    TIMEOUT
)


@dataclass(frozen=True)
class LoginPage:
    """Values from the authorize page that are needed to continue."""
    url: str
    # Bearer token for the /davinci endpoints
    sdk_token: str
    # Handle that ties the DaVinci result back to the suspended authorize
    # request. This is NOT the OAuth ``state``.
    resume_state: str

    @classmethod
    def parse(cls, url: str, html: str) -> "LoginPage":
        sk_props = _parse_sk_props(html)
        if not isinstance(sk_props.get("accessToken"), str):
            raise F1AuthError("No DaVinci SDK token in the authorize page.")

        parser = _StateInputParser()
        parser.feed(html)
        if not parser.state:
            raise F1AuthError(
                "Could not find the resume state in the authorize page.")

        return cls(url=url, sdk_token=sk_props["accessToken"],
                   resume_state=parser.state)


def sign_in(
        session: requests.Session,
        page: LoginPage,
        policy_id: str,
        username: str,
        password: str
) -> str:
    """Submit the credentials and return the ``dvResponse`` JWT."""
    headers = {
        "Origin": IDP_ORIGIN,
        "Referer": page.url,
        "Authorization": f"Bearer {page.sdk_token}",
    }

    resp = session.post(
        f"{DAVINCI_URL}/policy/{policy_id}/start",
        headers={**headers, "Content-Type": "application/json"},
        data=b"",
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        flow_id = data["id"]
        interaction_id = data["interactionId"]
        connection_id = data["connectionId"]
    except (KeyError, TypeError) as exc:
        raise F1AuthError(
            "Unexpected response when starting the sign-in.") from exc

    resp = session.post(
        f"{DAVINCI_URL}/connections/{connection_id}"
        f"/capabilities/customHTMLTemplate",
        json={
            "id": flow_id,
            "nextEvent": {
                "constructType": "skEvent",
                "eventName": "continue",
                "params": [],
                "eventType": "post",
                "postProcess": {},
            },
            "parameters": {
                "buttonType": "form-submit",
                "buttonValue": "SIGNIN",
                "username": username,
                "password": password,
            },
            "eventName": "continue",
            "interactionId": interaction_id,
        },
        headers={
            **headers,
            "interactionId": interaction_id,
            # the browser literally sends the string "undefined" here
            "interactionToken": "undefined",
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success") or not data.get("dvResponse"):
        raise F1AuthError(
            "Sign-in was rejected. Check username and password."
        )
    return data["dvResponse"]


def _parse_sk_props(html: str) -> dict:
    """Parse the ``var skProps = {...}`` JSON that bootstraps the SDK."""
    marker = "var skProps = "
    start = html.find(marker)
    if start < 0:
        raise F1AuthError(
            "Could not find 'var skProps' in the authorize page.")
    try:
        props, _ = json.JSONDecoder().raw_decode(html, start + len(marker))
    except json.JSONDecodeError as exc:
        raise F1AuthError("Malformed 'skProps' in the authorize page.") \
            from exc
    if not isinstance(props, dict):
        raise F1AuthError("Malformed 'skProps' in the authorize page.")
    return props


class _StateInputParser(HTMLParser):
    """Find the value of the ``<input name="state">`` element."""

    def __init__(self):
        super().__init__()
        self.state: str | None = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "input" and attributes.get("name") == "state":
            self.state = attributes.get("value")
