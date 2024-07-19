import pytest
from api_client import APIConfig, APIKeyAuth, OAuthAuth, BaseAPIClient, BearerTokenAuth, BasicAuth
from httpx import Request, Response
from pydantic import BaseModel

class MockAuth(AuthStrategy):
    """Mock authentication strategy for testing"""
    def authenticate(self, request: Request) -> None:
        request.headers['Authorization'] = 'MockAuth'

@pytest.fixture
def api_config():
    return APIConfig(base_url="https://api.example.com", api_key="dummy_api_key", oauth_token="dummy_oauth_token")

@pytest.fixture
def api_client(api_config):
    auth_strategy = MockAuth()
    return BaseAPIClient(api_config, auth_strategy)

def test_api_config(api_config):
    assert api_config.base_url == "https://api.example.com"
    assert api_config.api_key == "dummy_api_key"
    assert api_config.oauth_token == "dummy_oauth_token"
    assert api_config.retry_attempts == 3
    assert api_config.timeout == 10.0

def test_authenticate_with_api_key():
    auth = APIKeyAuth(api_key="dummy_api_key")
    request = Request(method="GET", url="https://api.example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"] == "Bearer dummy_api_key"

def test_authenticate_with_oauth():
    auth = OAuthAuth(token="dummy_oauth_token")
    request = Request(method="GET", url="https://api.example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"] == "Bearer dummy_oauth_token"

def test_authenticate_with_bearer_token():
    auth = BearerTokenAuth(token="dummy_bearer_token")
    request = Request(method="GET", url="https://api.example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"] == "Bearer dummy_bearer_token"

def test_authenticate_with_basic_auth():
    auth = BasicAuth(username="dummy_user", password="dummy_pass")
    request = Request(method="GET", url="https://api.example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"].startswith("Basic ")

def test_send_request(api_client, mocker):
    mocker.patch.object(api_client.client, 'send', return_value=Response(200, request=Request("GET", "https://api.example.com"), json={"key": "value"}))
    response = pytest.run(asyncio.run(api_client.send_request("GET", "/test")))
    assert response == {"key": "value"}

def test_get(api_client, mocker):
    mocker.patch.object(api_client.client, 'send', return_value=Response(200, request=Request("GET", "https://api.example.com"), json={"key": "value"}))
    response = pytest.run(asyncio.run(api_client.get("/test")))
    assert response == {"key": "value"}

def test_post(api_client, mocker):
    mocker.patch.object(api_client.client, 'send', return_value=Response(200, request=Request("POST", "https://api.example.com"), json={"key": "value"}))
    response = pytest.run(asyncio.run(api_client.post("/test")))
    assert response == {"key": "value"}
