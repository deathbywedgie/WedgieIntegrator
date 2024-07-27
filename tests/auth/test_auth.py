import pytest
from WedgieIntegrator.auth import BearerTokenAuth, BasicAuth, NoAuth, TokenAuth
from httpx import Request
import base64

def test_no_auth():
    auth = NoAuth()
    request = Request(method="GET", url="https://example.com")
    auth.authenticate(request)
    assert "Authorization" not in request.headers

def test_basic_auth():
    auth = BasicAuth(username="dummy_user", password="dummy_pass")
    request = Request(method="GET", url="https://example.com")
    auth.authenticate(request)
    expected_auth_header = "Basic " + base64.b64encode(b"dummy_user:dummy_pass").decode("utf-8")
    assert request.headers["Authorization"] == expected_auth_header

# @pytest.fixture
# def request():
#     return Request(method="GET", url="https://example.com")
#
# @pytest.mark.parametrize("auth_class, token, expected_header", [
#     (APIKeyAuth, "dummy_api_key", "Bearer dummy_api_key"),
#     (OAuthAuth, "dummy_oauth_token", "Bearer dummy_oauth_token"),
#     (BearerTokenAuth, "dummy_bearer_token", "Bearer dummy_bearer_token"),
# ])

def test_api_key_auth():
    auth = TokenAuth(token="dummy_api_key")
    request = Request(method="GET", url="https://example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"] == "Bearer dummy_api_key"

# def test_oauth_auth():
#     auth = OAuthAuth(token="dummy_oauth_token")
#     request = Request(method="GET", url="https://example.com")
#     auth.authenticate(request)
#     assert request.headers["Authorization"] == "Bearer dummy_oauth_token"

def test_bearer_token_auth():
    auth = BearerTokenAuth(token="dummy_bearer_token")
    request = Request(method="GET", url="https://example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"] == "Bearer dummy_bearer_token"
