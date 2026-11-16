"""Browser-based sign-in to the Formula 1 account (legacy method).

The user signs in on f1login.fastf1.dev in their own browser. A browser
addon then posts the F1 login session cookie to a short-lived local HTTP
server, which extracts the F1TV subscription token from it.

Storage and reuse of the token are handled by
:mod:`fastf1.internals.f1account`; this module only performs the sign-in.
"""

import json
import threading
import urllib.parse
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer
)

import jwt
import requests
from jwt.algorithms import RSAAlgorithm

from fastf1.exceptions import F1AuthError
from fastf1.internals.f1account.tokens import SubscriptionToken


JWKS_URL = "https://api.formula1.com/static/jwks.json"
LOGIN_URL = "https://f1login.fastf1.dev"


class _AuthServer(HTTPServer):
    """Local server that receives a single subscription token."""

    def __init__(self):
        super().__init__(("127.0.0.1", 0), _AuthHandler)
        self.token: str | None = None
        self.received = threading.Event()


class _AuthHandler(BaseHTTPRequestHandler):
    server: _AuthServer

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path != "/auth":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers["Content-Length"])
        data = json.loads(self.rfile.read(content_length).decode("utf-8"))
        cookie = json.loads(urllib.parse.unquote(data.get("loginSession")))

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())

        self.server.token = cookie.get("data", {}).get("subscriptionToken")
        self.server.received.set()


def login_browser() -> SubscriptionToken:
    """Sign in through the browser and return the livetiming token.

    Raises ``F1AuthError`` if no valid token is received.
    """
    with _AuthServer() as httpd:
        print(f"Please open the following URL in your browser to "
              f"authenticate FastF1 with your Formula1/F1TV account:\n"
              f"{LOGIN_URL}?port={httpd.server_port}\n")

        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        httpd.received.wait()
        httpd.shutdown()
        token = httpd.token

    if not token:
        raise F1AuthError("Sign-in returned no subscription token. "
                          "An active F1TV subscription is required.")
    try:
        _verify_jwt(token)
    except (jwt.PyJWTError, ValueError, requests.RequestException) as exc:
        raise F1AuthError(f"Token verification failed: {exc}") from exc

    return SubscriptionToken.from_jwt(token)


def _get_jwk(kid: str) -> dict:
    response = requests.get(JWKS_URL, timeout=30)
    response.raise_for_status()
    for key in response.json()["keys"]:
        if key["kid"] == kid:
            return key
    raise ValueError("Public key not found in JWKS for given kid.")


def _verify_jwt(token: str) -> dict:
    kid = jwt.get_unverified_header(token).get("kid")
    public_key = RSAAlgorithm.from_jwk(_get_jwk(kid))
    return jwt.decode(token, key=public_key, algorithms=["RS256"])
