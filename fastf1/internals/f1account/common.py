"""Shared constants of the sign-in package."""

ACCOUNT_ORIGIN = "https://account.formula1.com"

# identity provider (PingOne), which also hosts the DaVinci API
IDP_ORIGIN = "https://id.formula1.com"
AUTHORIZE_URL = f"{IDP_ORIGIN}/as/authorize"
RESUME_URL = f"{IDP_ORIGIN}/as/resume"
TOKEN_URL = f"{IDP_ORIGIN}/as/token"
DAVINCI_URL = f"{IDP_ORIGIN}/davinci"

# (connect, read) timeout in seconds for all sign-in requests
TIMEOUT = (5, 30)

# TODO: decide whether to send an honest FastF1 user agent instead of
#  impersonating a desktop browser
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-US,en;q=0.9",
}
