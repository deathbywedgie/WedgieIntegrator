import base64
from abc import ABC, abstractmethod
from typing import Union
from httpx import Request


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


class HeaderAuth(AuthStrategy):
    """Generic token authentication strategy"""
    header_name: str = "Authorization"
    header_prefix: str = None
    secret: Union[str, None] = None

    def __init__(self, secret: Union[str, None], header_name=None, header_prefix=None):
        self.__secret = secret
        if header_name is not None:
            self.header_name = header_name
        if header_prefix is not None:
            self.header_prefix = header_prefix

    def authenticate(self, request: Request):
        if not self.__secret:
            return
        if self.header_prefix:
            request.headers[self.header_name] = f"{self.header_prefix} {self.__secret}"
        else:
            request.headers[self.header_name] = self.__secret


class BasicAuth(HeaderAuth):
    """Basic authentication strategy"""
    header_prefix = "Basic"

    def __init__(self, username, password, header_name: str = None, header_prefix: str = None):
        if header_name is not None:
            self.header_name = header_name
        if header_prefix is not None:
            self.header_prefix = header_prefix
        basic_auth_str = f"{username}:{password}"
        super().__init__(secret=base64.b64encode(basic_auth_str.encode("utf-8")).decode("utf-8"))


class TokenAuth(HeaderAuth):
    """Generic token authentication strategy"""
    header_prefix: str = "Bearer"

    def __init__(self, token: str, header_name: str = None, header_prefix: str = None):
        if header_name is not None:
            self.header_name = header_name
        if header_prefix is not None:
            self.header_prefix = header_prefix
        super().__init__(secret=token)


class BearerTokenAuth(TokenAuth):
    """Bearer token authentication strategy"""

    def __init__(self, token: str):
        super().__init__(token=token)


# @dataclass
# class OAuthAuth(TokenAuth):
#     """OAuth token authentication strategy"""
#     token: str
#     header_name: str = "Authorization"
#     header_prefix: str = "Bearer"
