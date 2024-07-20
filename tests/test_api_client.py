import pytest
import httpx
from wedgieintegrator.client import BaseAPIClient
from wedgieintegrator.config import APIConfig
from wedgieintegrator.auth import APIKeyAuth, OAuthAuth, BasicAuth, BearerTokenAuth
from httpx import Request, Response
from unittest.mock import patch

class MockAuth(APIKeyAuth):
    """Mock authentication strategy for testing"""
    def authenticate(self, request: Request) -> None:
        request.headers['Authorization'] = 'MockAuth'

@pytest.fixture
def api_config():
    return APIConfig(base_url="https://api.example.com", api_key="dummy_api_key", oauth_token="dummy_oauth_token")

@pytest.fixture
def api_client(api_config):
    auth_strategy = MockAuth(api_key=api_config.api_key)
    return BaseAPIClient(config=api_config, auth_strategy=auth_strategy)

def test_api_config(api_config):
    """Test APIConfig initialization"""
    assert api_config.base_url == "https://api.example.com"
    assert api_config.api_key == "dummy_api_key"
    assert api_config.oauth_token == "dummy_oauth_token"
    assert api_config.retry_attempts == 3
    assert api_config.timeout == 10.0

def test_auth_with_api_key():
    """Test APIKeyAuth authentication"""
    auth = APIKeyAuth(api_key="dummy_api_key")
    request = Request(method="GET", url="https://api.example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"] == "Bearer dummy_api_key"

def test_auth_with_oauth():
    """Test OAuthAuth authentication"""
    auth = OAuthAuth(token="dummy_oauth_token")
    request = Request(method="GET", url="https://api.example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"] == "Bearer dummy_oauth_token"

def test_auth_with_bearer_token():
    """Test BearerTokenAuth authentication"""
    auth = BearerTokenAuth(token="dummy_bearer_token")
    request = Request(method="GET", url="https://api.example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"] == "Bearer dummy_bearer_token"

def test_auth_with_basic_auth():
    """Test BasicAuth authentication"""
    auth = BasicAuth(username="dummy_user", password="dummy_pass")
    request = Request(method="GET", url="https://api.example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"].startswith("Basic ")

@patch.object(httpx.AsyncClient, 'send', return_value=httpx.Response(200, request=Request("GET", "https://api.example.com"), json={"key": "value"}))
@pytest.mark.asyncio
async def test_send_request(mock_send, api_client):
    """Test sending an HTTP request"""
    response = await api_client.send_request(method="GET", endpoint="/test")
    assert response == {"key": "value"}
    assert mock_send.call_args[1]["method"] == "GET"

@patch.object(httpx.AsyncClient, 'send', return_value=httpx.Response(200, request=Request("GET", "https://api.example.com"), json={"key": "value"}))
@pytest.mark.asyncio
async def test_get(mock_send, api_client):
    """Test sending a GET request"""
    response = await api_client.get(endpoint="/test")
    assert response == {"key": "value"}
    assert mock_send.call_args[1]["method"] == "GET"

@patch.object(httpx.AsyncClient, 'send', return_value=httpx.Response(200, request=Request("POST", "https://api.example.com"), json={"key": "value"}))
@pytest.mark.asyncio
async def test_post(mock_send, api_client):
    """Test sending a POST request"""
    response = await api_client.post(endpoint="/test")
    assert response == {"key": "value"}
    assert mock_send.call_args[1]["method"] == "POST"

@pytest.mark.parametrize("auth_class, token, header_value", [
    (APIKeyAuth, "dummy_api_key", "Bearer dummy_api_key"),
    (OAuthAuth, "dummy_oauth_token", "Bearer dummy_oauth_token"),
    (BearerTokenAuth, "dummy_bearer_token", "Bearer dummy_bearer_token"),
])
def test_auth(auth_class, token, header_value):
    """Test different authentication strategies"""
    auth = auth_class(token)
    request = Request(method="GET", url="https://api.example.com")
    auth.authenticate(request)
    assert request.headers["Authorization"] == header_value

@patch.object(httpx.AsyncClient, 'send', side_effect=httpx.HTTPStatusError("Error", request=Request("GET", "https://api.example.com"), response=Response(400)))
@pytest.mark.asyncio
async def test_send_request_http_error(mock_send, api_client):
    """Test handling HTTP status errors in send_request"""
    with pytest.raises(httpx.HTTPStatusError):
        await api_client.send_request(method="GET", endpoint="/test")
