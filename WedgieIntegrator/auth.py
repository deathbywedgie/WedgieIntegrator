from abc import ABC, abstractmethod
from httpx import Request
import base64
from dataclasses import dataclass


class AuthStrategy(ABC):
    """Abstract base class for authentication strategies"""

    @abstractmethod
    def authenticate(self, request: Request):
        """Apply authentication to the request"""
        pass


class NoAuth(AuthStrategy):
    """No authentication strategy."""

    def authenticate(self, request: Request):
        pass


@dataclass
class BasicAuth(AuthStrategy):
    """Basic authentication strategy"""
    username: str
    password: str

    def authenticate(self, request: Request):
        basic_auth_str = f"{self.username}:{self.password}"
        encoded_auth_str = base64.b64encode(basic_auth_str.encode("utf-8")).decode("utf-8")
        request.headers['Authorization'] = f"Basic {encoded_auth_str}"


@dataclass
class TokenAuth(AuthStrategy):
    """Generic token authentication strategy"""
    token: str
    header_name: str
    header_prefix: str

    def authenticate(self, request: Request):
        if self.header_prefix:
            request.headers[self.header_name] = f"{self.header_prefix} {self.token}"
        else:
            request.headers[self.header_name] = self.token


@dataclass
class BearerTokenAuth(TokenAuth):
    """Bearer token authentication strategy"""
    token: str
    header_name: str = "Authorization"
    header_prefix: str = "Bearer"


@dataclass
class OAuthAuth(TokenAuth):
    """OAuth token authentication strategy"""
    token: str
    header_name: str = "Authorization"
    header_prefix: str = "Bearer"
