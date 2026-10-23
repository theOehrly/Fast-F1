import io
import json
import stat
import time

import jwt
import pytest
import requests
import urllib3
from requests.adapters import HTTPAdapter

import fastf1.internals.f1account as f1account
from fastf1.exceptions import F1AuthError
from fastf1.internals.f1account import (
    LIVETIMING_URL,
    LivetimingAuthAdapter,
    SubscriptionToken,
    TokenManager,
    browser,
    login
)
from fastf1.internals.f1account.discovery import (
    AuthConfig,
    parse_frontend_config
)
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
    'var a={clientId:"wrong"};var c={davinci:{clientId:"cid",'
    'registrationAcrValues:"rid",acrValues:"pid",'
    'redirectUri:window.location.origin+"/#//login/"},other:{acrValues:"x"}};'
)


def test_parse_frontend_config():
    assert parse_frontend_config(FRONTEND_SCRIPT) \
        == AuthConfig(client_id="cid", policy_id="pid")


def test_parse_frontend_config_missing_field():
    script = FRONTEND_SCRIPT.replace('acrValues:"pid",', "")
    with pytest.raises(F1AuthError, match="acrValues"):
        parse_frontend_config(script)


def test_parse_frontend_config_no_block():
    with pytest.raises(F1AuthError):
        parse_frontend_config("var a={b:1};")


# ---- login ----------------------------------------------------------------

def test_code_challenge():
    # test vector from RFC 7636, appendix B
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert login._code_challenge(verifier) \
        == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def _flow_response(data, status=200):
    resp = requests.Response()
    resp.status_code = status
    resp._content = json.dumps(data).encode()
    return resp


def test_code_from_flow_response():
    resp = _flow_response({"status": "COMPLETED", "authorizeResponse": {
        "code": "abc", "state": "xyz"}})
    assert login._code_from_flow_response(resp, "xyz") == "abc"


def test_code_from_flow_response_state_mismatch():
    resp = _flow_response({"status": "COMPLETED", "authorizeResponse": {
        "code": "abc", "state": "other"}})
    with pytest.raises(F1AuthError, match="state"):
        login._code_from_flow_response(resp, "xyz")


def test_code_from_flow_response_rejected():
    # response to wrong credentials
    resp = _flow_response({"code": "unexpectedError",
                           "message": "Check your details."}, status=400)
    with pytest.raises(F1AuthError, match="Check your details"):
        login._code_from_flow_response(resp, "xyz")


class _FakeLoginSession:
    """Answers the sign-in requests in order and records them."""

    def __init__(self, next_url="https://id.formula1.com/davinci/submit"):
        self.next_url = next_url
        self.calls = []

    def _respond(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        if url.endswith("/as/authorize"):
            return _flow_response({
                "id": "f", "interactionId": "i", "eventName": "continue",
                "_links": {"next": {"href": self.next_url}}})
        if url == self.next_url:
            state = self.calls[0][2]["params"]["state"]
            return _flow_response({"status": "COMPLETED",
                                   "authorizeResponse": {"code": "abc",
                                                         "state": state}})
        if url.endswith("/as/token"):
            return _flow_response({"access_token": "at"})
        raise AssertionError(f"unexpected request to {url}")

    def get(self, url, **kwargs):
        return self._respond("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self._respond("POST", url, **kwargs)


LOGIN_CONFIG = AuthConfig(client_id="cid", policy_id="pid")


def test_login_flow():
    session = _FakeLoginSession()
    assert login._do_login_flow(session, LOGIN_CONFIG, "user", "pw") == "at"

    authorize, submit, token = session.calls
    params = authorize[2]["params"]
    assert params["acr_values"] == "pid"
    assert params["response_mode"] == "pi.flow"
    assert submit[2]["headers"]["interactionId"] == "i"
    assert submit[2]["json"]["parameters"]["data"]["formData"] \
        == {"username": "user", "password": "pw"}
    data = token[2]["data"]
    assert data["code"] == "abc"
    assert "redirect_uri" not in data
    assert login._code_challenge(data["code_verifier"]) \
        == params["code_challenge"]


def test_login_flow_rejects_foreign_submit_url():
    session = _FakeLoginSession(next_url="https://evil.example.com/submit")
    with pytest.raises(F1AuthError, match="url"):
        login._do_login_flow(session, LOGIN_CONFIG, "user", "pw")
    assert len(session.calls) == 1  # credentials were not sent


def test_login_extracts_subscription_token(monkeypatch):
    sub = _jwt(exp=int(time.time() + 100))
    monkeypatch.setattr(login, "fetch_config", lambda session: None)
    monkeypatch.setattr(login, "_do_login_flow",
                        lambda *args: _jwt(subscriptionToken=sub))
    assert login.login("user", "pw").value == sub

    monkeypatch.setattr(login, "_do_login_flow", lambda *args: _jwt(sub="x"))
    with pytest.raises(F1AuthError, match="subscription"):
        login.login("user", "pw")


# ---- tokens ---------------------------------------------------------------

def test_token_from_jwt():
    exp = int(time.time() + 100)
    token = SubscriptionToken.from_jwt(_jwt(exp=exp, SubscribedProduct="Pro"))
    assert token.expires_at == exp
    assert token.claims["SubscribedProduct"] == "Pro"


def test_token_from_jwt_without_expiry():
    with pytest.raises(F1AuthError, match="expiry"):
        SubscriptionToken.from_jwt(_jwt(sub="x"))
    with pytest.raises(F1AuthError, match="expiry"):
        SubscriptionToken.from_jwt("not-a-jwt")


def test_token_repr_hides_value():
    assert "secret-value" not in repr(_token("secret-value"))


def test_token_store_roundtrip_and_permissions(tmp_path):
    path = tmp_path / "token.json"
    path.write_text("{}")
    path.chmod(0o644)

    store = TokenManager(lambda: _token(), path)
    token = _token()
    store.store(token)

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert store.get_stored() == token
    assert list(tmp_path.iterdir()) == [path]  # no leftover temp file

    store.clear()
    assert store.get_stored() is None


def test_token_store_ignores_invalid_file(tmp_path):
    path = tmp_path / "token.json"
    path.write_text('{"subscription_token": "x", "expires_at": 1}')
    assert TokenManager(lambda: _token(), path).get_stored() is None


def test_token_manager_signs_in_once(tmp_path):
    calls = []

    def authenticate():
        calls.append(1)
        return _token()

    manager = TokenManager(authenticate, tmp_path / "t.json")
    assert manager.get() is manager.get()
    assert len(calls) == 1

    # a new manager picks the token up from disk
    other = TokenManager(authenticate, tmp_path / "t.json")
    assert other.get() == manager.get()
    assert len(calls) == 1


def test_token_manager_renews_expired_token(tmp_path):
    tokens = iter([_token("old", lifetime=0), _token("new")])
    manager = TokenManager(lambda: next(tokens), tmp_path / "t.json")
    assert manager.get().value == "old"
    assert manager.get().value == "new"


def test_token_manager_authenticate_override(tmp_path):
    manager = TokenManager(lambda: _token("default"), tmp_path / "t.json")
    assert manager.get(auth_func=lambda: _token("other")).value == "other"
    # a valid token is reused, unless renewal is forced
    assert manager.get(auth_func=lambda: _token("x")).value == "other"
    assert manager.get(force_renew=True).value == "default"


# ---- sign-in method -------------------------------------------------------

@pytest.fixture
def auth_method(monkeypatch):
    monkeypatch.delenv(f1account.ENV_AUTH_METHOD, raising=False)
    yield
    f1account.set_auth_method(None)


def test_auth_method_precedence(auth_method, monkeypatch):
    assert f1account.get_auth_method() == "password"
    monkeypatch.setenv(f1account.ENV_AUTH_METHOD, "browser")
    assert f1account.get_auth_method() == "browser"
    f1account.set_auth_method("password")
    assert f1account.get_auth_method() == "password"


def test_auth_method_invalid(auth_method, monkeypatch):
    with pytest.raises(ValueError, match="password, browser"):
        f1account.set_auth_method("oauth")
    monkeypatch.setenv(f1account.ENV_AUTH_METHOD, "oauth")
    with pytest.raises(ValueError):
        f1account.get_auth_method()


def test_authenticators():
    assert f1account.AUTH_METHODS == ("password", "browser")
    assert f1account._AUTHENTICATORS["browser"] is browser.login_browser
    assert f1account._AUTHENTICATORS["password"] is login.default_login


def test_get_token_uses_method(auth_method, monkeypatch, tmp_path):
    for method in f1account.AUTH_METHODS:
        monkeypatch.setitem(f1account._AUTHENTICATORS, method,
                            lambda method=method: _token(method))

    monkeypatch.setattr(f1account.token_manager, "_token_path",
                        tmp_path / "t.json")
    monkeypatch.setattr(f1account.token_manager, "_token", None)

    assert f1account.get_token().value == "password"
    assert f1account.get_token(True, method="browser").value == "browser"
    f1account.set_auth_method("browser")
    assert f1account.get_token(True).value == "browser"
    with pytest.raises(ValueError):
        f1account.get_token(True, method="oauth")


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
