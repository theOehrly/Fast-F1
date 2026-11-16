"""The livetiming token, its file storage and access to it."""

import contextlib
import json
import os
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
from fastf1.internals.f1account.common import logger


# renew the token if it expires within this many seconds
EXPIRY_MARGIN = 300


@dataclass(frozen=True)
class SubscriptionToken:
    """F1TV entitlement JWT, sent as Bearer token to F1 APIs."""
    value: str = field(repr=False)
    expires_at: float

    @classmethod
    def from_jwt(cls, value: str) -> "SubscriptionToken":
        """Create the token from the subscription JWT, taking the expiry
        from its ``exp`` claim."""
        try:
            expires_at = float(_unverified_claims(value)["exp"])
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise F1AuthError("Subscription token has no valid expiry.") \
                from exc
        return cls(value=value, expires_at=expires_at)

    @property
    def claims(self) -> dict:
        """The unverified claims of the token, e.g. the subscription
        status."""
        return _unverified_claims(self.value)

    @property
    def authorization_header(self) -> str:
        return f"Bearer {self.value}"

    def is_valid(self) -> bool:
        return self.expires_at - EXPIRY_MARGIN > time.time()


def _unverified_claims(token: str) -> dict:
    # the token is only read here; the API verifies the signature
    return jwt.decode(token, options={"verify_signature": False})


class TokenManager:
    """Provides a valid token, signing in only when needed.

    Args:
        auth_func: performs the sign-in and returns a new token
        path: where to store the token
    """
    VERSION = 1

    def __init__(
            self,
            auth_func: Callable[[], SubscriptionToken],
            path: Path | None = None
    ):
        if path is None:
            # Default path should be the user data dir. On Windows, this also
            # ensures that the token is not accessible by other users.
            self._token_path = Path(
                platformdirs.user_data_dir("fastf1")) / "f1auth_token.json"
        else:
            self._token_path = path
        self._default_auth_func = auth_func
        self._token: SubscriptionToken | None = None

    def get(
            self,
            force_renew: bool = False,
            auth_func: Callable[[], SubscriptionToken] | None = None
    ) -> SubscriptionToken:
        """Return a valid token from memory or disk, or sign in.

        Args:
            force_renew: sign in even if a valid token exists
            auth_func: sign in with this instead of the default
        """
        if not force_renew:
            token = self.get_stored()
            if token is not None and token.is_valid():
                return token

        logger.info("Signing in to Formula 1 account...")

        if auth_func is not None:
            self._token = auth_func()
        else:
            self._token = self._default_auth_func()
        logger.info("Sign-in successful.")

        try:
            self.store(self._token)
        except OSError as exc:
            logger.warning(f"Failed to store the access token: {exc}")
        return self._token

    def get_stored(self) -> SubscriptionToken | None:
        """Return the token from memory or disk without signing in. The
        token may be expired."""
        if self._token is not None:
            return self._token

        try:
            data = json.loads(self._token_path.read_text())
            if data.pop("version") != self.VERSION:
                return None
            return SubscriptionToken(**data)
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            return None

    def store(self, token: SubscriptionToken):
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._token_path, "w") as f:
            # restrict access to this user before writing the token
            # has no effect on Windows, but the token path defaults to
            # the user data dir to prevent unauthorized access
            os.chmod(self._token_path, 0o600)
            json.dump({"version": self.VERSION, **asdict(token)}, f)

    def clear(self):
        """Remove the token from memory and disk."""
        self._token = None
        with contextlib.suppress(FileNotFoundError):
            self._token_path.unlink()
