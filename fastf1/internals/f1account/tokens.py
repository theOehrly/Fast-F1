"""The livetiming token, its file storage and access to it."""

import contextlib
import json
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import (
    asdict,
    dataclass,
    field
)
from pathlib import Path

import jwt
import platformdirs

from fastf1.exceptions import F1AuthError
from fastf1.logger import get_logger


_logger = get_logger(__name__)

# renew the token if it expires within this many seconds
EXPIRY_MARGIN = 300

# assumed lifetime if neither the server nor the token states an expiry
DEFAULT_LIFETIME = 3600


@dataclass(frozen=True)
class SubscriptionToken:
    """F1TV entitlement JWT, sent as Bearer token to livetiming."""
    value: str = field(repr=False)
    expires_at: float

    @classmethod
    def from_access_token(
            cls, access_token: str, expires_at: float | None = None
    ) -> "SubscriptionToken":
        """Extract the token from the ``subscriptionToken`` claim of the
        OAuth access token, which itself is rejected by livetiming."""
        try:
            claims = _unverified_claims(access_token)
        except jwt.PyJWTError as exc:
            raise F1AuthError("Failed to decode the access token.") from exc
        value = claims.get("subscriptionToken")
        if not value:
            raise F1AuthError("Access token contains no subscription token. "
                              "An active F1TV subscription is required.")

        # the subscription token may expire before the access token
        candidates = [expires_at] if expires_at else []
        with contextlib.suppress(jwt.PyJWTError, TypeError, ValueError):
            if exp := _unverified_claims(value).get("exp"):
                candidates.append(float(exp))
        return cls(value=value, expires_at=min(
            candidates, default=time.time() + DEFAULT_LIFETIME))

    @property
    def authorization_header(self) -> str:
        return f"Bearer {self.value}"

    def is_valid(self) -> bool:
        return self.expires_at - EXPIRY_MARGIN > time.time()


def _unverified_claims(token: str) -> dict:
    # the token is only read here; livetiming verifies the signature
    return jwt.decode(token, options={"verify_signature": False})


class TokenStore:
    """Persists the token in a JSON file that only the owner can read."""

    VERSION = 1

    def __init__(self, path: Path):
        self.path = path

    @classmethod
    def default(cls) -> "TokenStore":
        return cls(Path(platformdirs.user_data_dir("fastf1"))
                   / "f1auth_token.json")

    def load(self) -> SubscriptionToken | None:
        try:
            data = json.loads(self.path.read_text())
            if data.pop("version") != self.VERSION:
                return None
            return SubscriptionToken(**data)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return None

    def save(self, token: SubscriptionToken):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # mkstemp creates the file with mode 0600; replacing the target
        # makes the write atomic and fixes the mode of an existing file
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent,
                                        prefix=f".{self.path.name}.")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"version": self.VERSION, **asdict(token)}, f)
            os.replace(tmp_path, self.path)
        except BaseException:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(tmp_path)
            raise

    def delete(self):
        with contextlib.suppress(FileNotFoundError):
            self.path.unlink()


class TokenManager:
    """Provides a valid token, signing in only when needed.

    Args:
        store: persistent storage for the token
        authenticate: performs the sign-in and returns a new token
    """

    def __init__(
            self,
            store: TokenStore,
            authenticate: Callable[[], SubscriptionToken]
    ):
        self._store = store
        self._authenticate = authenticate
        self._token: SubscriptionToken | None = None

    def get(self, force_renew: bool = False) -> SubscriptionToken:
        """Return a valid token from memory or disk, or sign in."""
        if not force_renew:
            self._token = self._token or self._store.load()
            if self._token is not None and self._token.is_valid():
                return self._token

        _logger.info("Signing in to Formula 1 account...")
        self._token = self._authenticate()
        _logger.info("Sign-in successful.")
        try:
            self._store.save(self._token)
        except OSError as exc:
            _logger.warning(f"Failed to store the access token: {exc}")
        return self._token

    def clear(self):
        """Remove the token from memory and disk."""
        self._token = None
        self._store.delete()
