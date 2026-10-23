"""Shared constants of the sign-in package."""

from fastf1.logger import get_logger


logger = get_logger("f1account")

ACCOUNT_ORIGIN = "https://account.formula1.com"

# identity provider (PingOne), which also hosts the DaVinci API
IDP_ORIGIN = "https://id.formula1.com"
AUTHORIZE_URL = f"{IDP_ORIGIN}/as/authorize"
TOKEN_URL = f"{IDP_ORIGIN}/as/token"

# (connect, read) timeout in seconds for all sign-in requests
TIMEOUT = (5, 30)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
}
