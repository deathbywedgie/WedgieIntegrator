from abc import ABC, abstractmethod
import httpx
import base64

class AuthStrategy(ABC):
    """Abstract base class for authentication strategies"""

    @abstractmethod
    def authenticate(self, request: httpx.Request):
        """Apply authentication to the request"""
        pass

class APIKeyAuth(AuthStrategy):
    """API key authentication strategy"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def authenticate(self, request: httpx.Request):
        request.headers['Authorization'] = f"Bearer {self.api_key}"

class BasicAuth(AuthStrategy):
    """Basic authentication strategy"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def authenticate(self, request: httpx.Request):
        basic_auth_str = f"{self.username}:{self.password}"
        encoded_auth_str = base64.b64encode(basic_auth_str.encode("utf-8")).decode("utf-8")
        request.headers['Authorization'] = f"Basic {encoded_auth_str}"

class BearerTokenAuth(AuthStrategy):
    """Bearer token authentication strategy"""

    def __init__(self, token: str):
        self.token = token

    def authenticate(self, request: httpx.Request):
        request.headers['Authorization'] = f"Bearer {self.token}"

class NoAuth(AuthStrategy):
    """No authentication strategy."""

    def authenticate(self, request: httpx.Request):
        pass

class OAuthAuth(AuthStrategy):
    """OAuth token authentication strategy"""

    def __init__(self, token: str):
        self.token = token

    def authenticate(self, request: httpx.Request):
        request.headers['Authorization'] = f"Bearer {self.token}"
