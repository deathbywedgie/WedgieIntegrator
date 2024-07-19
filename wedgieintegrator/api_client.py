from pydantic import BaseModel, ValidationError
from abc import ABC, abstractmethod
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from typing import Optional, Any, Type, Union
import structlog
import logging

# Configure structlog
def configure_structlog():
    """Configure structlog if it has not been configured by the user"""
    if not structlog.is_configured():
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING)
        )

configure_structlog()
logger = structlog.get_logger()

class APIConfig(BaseModel):
    """Configuration model for API client"""
    base_url: str
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None
    retry_attempts: int = 3
    timeout: Optional[float] = 10.0  # Default timeout of 10 seconds

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

class OAuthAuth(AuthStrategy):
    """OAuth token authentication strategy"""

    def __init__(self, token: str):
        self.token = token

    def authenticate(self, request: httpx.Request):
        request.headers['Authorization'] = f"Bearer {self.token}"

class BearerTokenAuth(AuthStrategy):
    """Bearer token authentication strategy"""

    def __init__(self, token: str):
        self.token = token

    def authenticate(self, request: httpx.Request):
        request.headers['Authorization'] = f"Bearer {self.token}"

class BasicAuth(AuthStrategy):
    """Basic authentication strategy"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def authenticate(self, request: httpx.Request):
        request.headers['Authorization'] = f"Basic {httpx.BasicAuth(self.username, self.password).auth_header}"

class NoAuth(AuthStrategy):
    """No authentication strategy."""

    def authenticate(self, request: httpx.Request):
        pass

def with_retries(func):
    """Decorator to add retries to a function based on config"""
    def wrapper(self, *args, **kwargs):
        retry_decorator = retry(stop=stop_after_attempt(self.config.retry_attempts), wait=wait_exponential(min=1, max=10))
        return retry_decorator(func)(self, *args, **kwargs)
    return wrapper

class BaseAPIClient:
    """Base class for API client"""

    def __init__(self, config: APIConfig, auth_strategy: AuthStrategy, response_model: Optional[Type[BaseModel]] = None):
        self.config = config
        self.auth_strategy = auth_strategy
        self.response_model = response_model
        self.client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(base_url=self.config.base_url, timeout=self.config.timeout)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.client.aclose()

    @with_retries
    async def send_request(self, method: str, endpoint: str, **kwargs: Any) -> Union[dict, Any]:
        """Send an HTTP request with retries and authentication"""
        logger.info("Sending request", method=method, endpoint=endpoint, params=kwargs)
        if self.client is None:
            raise RuntimeError("HTTP client is not initialized")

        request = self.client.build_request(method, endpoint, **kwargs)
        self.auth_strategy.authenticate(request)
        try:
            response = await self.client.send(request)
            response.raise_for_status()
            logger.info("Received response", status_code=response.status_code, content=response.text)
            if self.response_model:
                return self.response_model.parse_obj(response.json())
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error occurred", status_code=e.response.status_code, content=e.response.text)
            raise
        except RetryError as e:
            logger.error("Retry failed", error=str(e))
            raise
        except ValidationError as e:
            logger.error("Response validation failed", error=str(e))
            raise

    async def get(self, endpoint: str, **kwargs: Any) -> Union[dict, Any]:
        """Send a GET request"""
        return await self.send_request("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs: Any) -> Union[dict, Any]:
        """Send a POST request"""
        return await self.send_request("POST", endpoint, **kwargs)
