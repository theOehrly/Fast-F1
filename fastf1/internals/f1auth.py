import json
import threading
import urllib.parse
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer
)
from pathlib import Path

import jwt
import platformdirs
import requests
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import (
    InvalidTokenError,
    PyJWTError
)

from fastf1.logger import get_logger


JWKS_URL = "https://api.formula1.com/static/jwks.json"
USER_DATA_DIR = Path(platformdirs.user_data_dir("fastf1", ensure_exists=True))
AUTH_DATA_FILE = USER_DATA_DIR / "f1auth.json"
AUTH_DATA_FILE.touch(exist_ok=True)

_auth_finished = threading.Event()
_subscription_data: None | dict = None

_logger = get_logger(__name__)


class AuthHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path == '/auth':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            cookie = data.get("loginSession")
            decoded_string = urllib.parse.unquote(cookie)
            parsed_data = json.loads(decoded_string)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

            global _subscription_data
            _subscription_data = parsed_data
            _auth_finished.set()


def _run_auth_server():
    server_address = ('127.0.0.1', 0)
    httpd = HTTPServer(server_address, AuthHandler)
    port = httpd.server_port

    print(f'Please open the following URL in your browser to '
          f'authenticate FastF1 with your Formula1/F1TV account:\n'
          f'https://f1login.fastf1.dev?port={port}\n')

    _auth_finished.clear()
    t = threading.Thread(target=httpd.serve_forever)
    t.start()
    _auth_finished.wait()
    httpd.shutdown()

    try:
        _verify_jwt(_subscription_data['data']['subscriptionToken'], JWKS_URL)
    except PyJWTError:
        _logger.error("Unknown error encountered: sign-in successful, "
                      "but token verification failed.")


def _get_jwk_from_jwks_uri(jwks_uri, kid):
    # Fetch the JWKS data from the URL
    response = requests.get(jwks_uri)
    response.raise_for_status()
    jwks = response.json()

    # Find the key with the matching 'kid'
    for key in jwks['keys']:
        if key['kid'] == kid:
            return key
    raise ValueError("Public key not found in JWKS for given kid.")


def _verify_jwt(token, jwks_uri, audience=None, issuer=None):
    # Decode headers to get the kid
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get('kid')
    jwk = _get_jwk_from_jwks_uri(jwks_uri, kid)

    # Convert JWK to public key
    public_key = RSAAlgorithm.from_jwk(jwk)

    # Verify and decode the token
    payload = jwt.decode(
        token,
        key=public_key,
        algorithms="RS256",
        audience=audience,
        issuer=issuer,
        verify=True
    )

    return payload


def get_auth_token():
    """Get the authentication token."""
    # TODO: add option to override from env var and dotenv file

    global _subscription_data
    token = None

    if _subscription_data is None:
        try:
            with open(AUTH_DATA_FILE) as f:
                _subscription_data = json.load(f)
        except json.JSONDecodeError:
            # expected if file is empty
            pass

    if _subscription_data is not None:
        token = _subscription_data['data']['subscriptionToken']

    if token is None:
        print("\nThis feature requires an active F1TV Access/Pro/Premium "
              "subscription.\n")

    # TODO: add option to ignore expiry
    if token is not None:
        # if token is already known, validate it
        try:
            _verify_jwt(token, JWKS_URL)
        except InvalidTokenError:
            print("Subscription token is invalid. Please re-authenticate.")
            _subscription_data = None
            token = None
        except PyJWTError:
            print("Unknown error occurred while validating token. "
                  "Please re-authenticate.")
            _subscription_data = None
            token = None

    if _subscription_data is None:
        # no token found or token is invalid, user needs to authenticate
        _run_auth_server()
        with open(AUTH_DATA_FILE, 'w') as f:
            json.dump(_subscription_data, f)
        token = _subscription_data['data']['subscriptionToken']

    return token
