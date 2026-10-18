import io
import stat
import time

import jwt
import pytest
import requests
import urllib3
from requests.adapters import HTTPAdapter

from fastf1.exceptions import F1AuthError
from fastf1.internals.f1account import (
    LIVETIMING_URL,
    LivetimingAuthAdapter,
    SubscriptionToken,
    TokenManager,
    TokenStore
)
from fastf1.internals.f1account.davinci import LoginPage
from fastf1.internals.f1account.discovery import (
    AuthConfig,
    parse_frontend_config
)
from fastf1.internals.f1account.tokens import DEFAULT_LIFETIME
from fastf1.req import (
    _CachedSessionWithRateLimiting,
    _SessionWithRateLimiting
)


def _jwt(**claims):
    # test secret needs to have a minimum length to be considered secure
    return jwt.encode(claims, "test-secret" * 4, algorithm="HS256")


def _token(value="tok", lifetime=3600):
    return SubscriptionToken(value=value, expires_at=time.time() + lifetime)


# ---- discovery ------------------------------------------------------------

FRONTEND_SCRIPT = (
    'var a={x:1};var c={davinci:{clientId:"cid",acrValues:"pid",'
    'nested:{key:"}"},scope:"openid profile",'
    'redirectUri:window.location.origin+"/#//login/"'
    '},other:{clientId:"wrong"}};'
)


def test_parse_frontend_config():
    assert parse_frontend_config(FRONTEND_SCRIPT) == AuthConfig(
        client_id="cid",
        policy_id="pid",
        scope="openid profile",
        redirect_uri="https://account.formula1.com/#//login/",
    )


def test_parse_frontend_config_missing_field():
    script = FRONTEND_SCRIPT.replace('scope:"openid profile",', '')
    with pytest.raises(F1AuthError, match="scope"):
        parse_frontend_config(script)


def test_parse_frontend_config_no_block():
    with pytest.raises(F1AuthError):
        parse_frontend_config("var a={b:1};")


# ---- davinci --------------------------------------------------------------

SK_PROPS = ('<script>var skProps = {"accessToken": "sdk", "x": "{}"};'
            '</script>')
RESUME_FORM = (
    '<form id="pingOneDaVinciResponseForm" method="POST">'
    '<input type="hidden" name="dvResponse" value="">'
    '<input type="hidden" value="resume" name="state">'
    '</form>'
)


def test_login_page_parse():
    html = SK_PROPS + RESUME_FORM
    page = LoginPage.parse("https://id.example.com/as/authorize?x=1", html)
    assert page.sdk_token == "sdk"
    assert page.resume_state == "resume"


def test_login_page_parse_missing_resume_state():
    with pytest.raises(F1AuthError, match="resume state"):
        LoginPage.parse("https://id.example.com/as/authorize", SK_PROPS)


def test_login_page_parse_missing_sdk_token():
    html = '<script>var skProps = {"x": 1};</script>' + RESUME_FORM
    with pytest.raises(F1AuthError, match="SDK token"):
        LoginPage.parse("https://id.example.com/as/authorize", html)


# ---- tokens ---------------------------------------------------------------

def test_token_from_access_token_uses_earliest_expiry():
    now = time.time()
    sub = _jwt(exp=int(now + 100))
    token = SubscriptionToken.from_access_token(
        _jwt(subscriptionToken=sub), expires_at=now + 1000)
    assert token.value == sub
    assert token.expires_at == int(now + 100)


def test_token_from_access_token_without_expiry():
    # neither the token response nor the token state an expiry
    token = SubscriptionToken.from_access_token(
        _jwt(subscriptionToken=_jwt(sub="x")))
    assert token.expires_at == pytest.approx(time.time() + DEFAULT_LIFETIME,
                                             abs=5)
    assert token.is_valid()


def test_token_from_access_token_without_subscription():
    with pytest.raises(F1AuthError, match="subscription"):
        SubscriptionToken.from_access_token(_jwt(sub="x"))


def test_token_repr_hides_value():
    assert "secret-value" not in repr(_token("secret-value"))


def test_token_store_roundtrip_and_permissions(tmp_path):
    path = tmp_path / "token.json"
    path.write_text("{}")
    path.chmod(0o644)

    store = TokenStore(path)
    token = _token()
    store.save(token)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert store.load() == token
    assert list(tmp_path.iterdir()) == [path]  # no leftover temp file

    store.delete()
    assert store.load() is None


def test_token_store_ignores_invalid_file(tmp_path):
    path = tmp_path / "token.json"
    path.write_text('{"subscription_token": "x", "expires_at": 1}')
    assert TokenStore(path).load() is None


def test_token_manager_signs_in_once(tmp_path):
    calls = []

    def authenticate():
        calls.append(1)
        return _token()

    manager = TokenManager(TokenStore(tmp_path / "t.json"), authenticate)
    assert manager.get() is manager.get()
    assert len(calls) == 1

    # a new manager picks the token up from disk
    other = TokenManager(TokenStore(tmp_path / "t.json"), authenticate)
    assert other.get() == manager.get()
    assert len(calls) == 1


def test_token_manager_renews_expired_token(tmp_path):
    tokens = iter([_token("old", lifetime=0), _token("new")])
    manager = TokenManager(TokenStore(tmp_path / "t.json"),
                           lambda: next(tokens))
    assert manager.get().value == "old"
    assert manager.get().value == "new"


# ---- transport ------------------------------------------------------------

class _FakeTokens:
    def __init__(self, *tokens, error=None):
        self._tokens = list(tokens)
        self._error = error
        self.cleared = []
        self.calls = 0

    def get(self):
        self.calls += 1
        if self._error:
            raise self._error
        return self._tokens[0]

    def clear(self):
        self.cleared.append(self._tokens.pop(0))


@pytest.fixture
def sent(monkeypatch):
    """Replace the network layer; record requests, reply 401 to "bad"."""
    requests_sent = []

    def fake_send(self, request, **kwargs):
        requests_sent.append(request)
        auth = request.headers.get("Authorization")
        raw = urllib3.HTTPResponse(
            body=io.BytesIO(b"{}"),
            status=401 if auth == "Bearer bad" else 200,
            headers={"Content-Type": "application/json"},
            preload_content=False,
            request_url=request.url,
        )
        return self.build_response(request, raw)

    def dispatch_to_adapter(self, request, **kwargs):
        # the test setup blocks ``Session.send`` globally; only the adapter
        # dispatch of the original implementation is needed here
        return self.get_adapter(request.url).send(request, **kwargs)

    monkeypatch.setattr(HTTPAdapter, "send", fake_send)
    monkeypatch.setattr(requests.Session, "send", dispatch_to_adapter)
    return requests_sent


def _session(tokens, session_cls=requests.Session, **kwargs):
    session = session_cls(**kwargs)
    session.mount(LIVETIMING_URL, LivetimingAuthAdapter(tokens))
    return session


def test_adapter_adds_token(sent):
    session = _session(_FakeTokens(_token("good")))
    req = requests.Request("GET", LIVETIMING_URL + "static/a.json").prepare()
    resp = session.send(req)

    assert resp.status_code == 200
    assert sent[0].headers["Authorization"] == "Bearer good"
    assert "Authorization" not in req.headers  # caller's request unchanged


def test_adapter_retries_once_after_401(sent):
    tokens = _FakeTokens(_token("bad"), _token("good"))
    resp = _session(tokens).get(LIVETIMING_URL + "static/a.json")

    assert resp.status_code == 200
    assert [r.headers["Authorization"] for r in sent] \
        == ["Bearer bad", "Bearer good"]
    assert [t.value for t in tokens.cleared] == ["bad"]


def test_adapter_without_token_sends_unauthenticated(sent):
    tokens = _FakeTokens(error=F1AuthError("no credentials"))
    resp = _session(tokens).get(LIVETIMING_URL + "static/a.json")

    assert resp.status_code == 200
    assert "Authorization" not in sent[0].headers


def test_adapter_not_used_for_other_hosts(sent):
    tokens = _FakeTokens(_token("good"))
    _session(tokens).get("https://livetiming-mirror.example.com/a.json")

    assert tokens.calls == 0
    assert "Authorization" not in sent[0].headers


def test_adapter_not_used_for_cache_hits(sent):
    tokens = _FakeTokens(_token("good"))
    session = _session(tokens, _CachedSessionWithRateLimiting,
                       backend="memory")
    url = LIVETIMING_URL + "static/a.json"

    assert not session.get(url).from_cache
    assert session.get(url).from_cache
    assert tokens.calls == 1
    assert len(sent) == 1

    # the token is not persisted in the cache
    cached = session.cache.get_response(session.cache.create_key(
        requests.Request("GET", url).prepare()))
    assert cached.request.headers.get("Authorization") != "Bearer good"


def test_fastf1_sessions_mount_adapter():
    session = _SessionWithRateLimiting()
    assert isinstance(session.get_adapter(LIVETIMING_URL + "static/a.json"),
                      LivetimingAuthAdapter)
    assert not isinstance(
        session.get_adapter("https://livetiming-mirror.example.com/a.json"),
        LivetimingAuthAdapter
    )
