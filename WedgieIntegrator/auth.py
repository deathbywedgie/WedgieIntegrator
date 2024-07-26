from abc import ABC, abstractmethod
import httpx
import base64

class AuthStrategy(ABC):
    """Abstract base class for authentication strategies"""

    @abstractmethod
    def authenticate(self, request: httpx.Request):
        """Apply authentication to the request"""
        pass

class NoAuth(AuthStrategy):
    """No authentication strategy."""

    def authenticate(self, request: httpx.Request):
        pass

class BasicAuth(AuthStrategy):
    """Basic authentication strategy"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def authenticate(self, request: httpx.Request):
        basic_auth_str = f"{self.username}:{self.password}"
        encoded_auth_str = base64.b64encode(basic_auth_str.encode("utf-8")).decode("utf-8")
        request.headers['Authorization'] = f"Basic {encoded_auth_str}"

class TokenAuth(AuthStrategy):
    """Bearer token authentication strategy"""

    def __init__(self, token: str, header_name: str, header_prefix: str):
        self.token = token
        self.header_name = header_name
        self.header_prefix = header_prefix

    def authenticate(self, request: httpx.Request):
        if self.header_prefix:
            request.headers[self.header_name] = f"{self.header_prefix} {self.token}"
        else:
            request.headers[self.header_name] = self.token

class BearerTokenAuth(TokenAuth):
    """Bearer token authentication strategy"""

    def __post_init__(self, token: str):
        super().__init__(token=token, header_name="Authorization", header_prefix="Bearer")

class OAuthAuth(TokenAuth):
    """OAuth token authentication strategy"""

    def __post_init__(self, token: str):
        super().__init__(token=token, header_name="Authorization", header_prefix="Bearer")
