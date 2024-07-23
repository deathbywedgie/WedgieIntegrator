from pydantic import BaseModel, ValidationError
import httpx
from tenacity import RetryError
from typing import Optional, Any, Type, Union
import structlog
from .logging_config import configure_structlog
from .config import APIConfig
from .auth import AuthStrategy

# Configure structlog
configure_structlog()
logger = structlog.get_logger()

class BaseAPIClient:
    """Base class for API client"""

    def __init__(self, config: APIConfig, auth_strategy: AuthStrategy, response_model: Optional[Type[BaseModel]] = None):
        self.config = config
        self.auth_strategy = auth_strategy
        self.response_model = response_model
        # Initialize client here
        self.client = httpx.AsyncClient(
            base_url=self.config.base_url, timeout=self.config.timeout, verify=self.config.verify_ssl)

    async def __aenter__(self) -> 'BaseAPIClient':
        # No need to initialize the client here as it is already initialized in __init__
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[Any]):
        if self.client:
            await self.client.aclose()

    async def _send_request(self, method: str, endpoint: str, raise_for_status=True, **kwargs: Any) -> httpx.Response:
        """Send an HTTP request with retries and authentication"""
        logger.info("Sending request", method=method, endpoint=endpoint, params=kwargs)
        if self.client is None:
            raise RuntimeError("HTTP client is not initialized")

        request = self.client.build_request(method=method, url=endpoint, **kwargs)
        self.auth_strategy.authenticate(request)
        try:
            response = await self.client.send(request)
            logger.info("Received response", status_code=response.status_code)
            if raise_for_status:
                response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error occurred", status_code=e.response.status_code, content=e.response.text)
            raise
        except RetryError as e:
            logger.error("Retry failed", error=str(e))
            raise

    async def send_request(self, method: str, endpoint: str, raise_for_status=True, return_response: bool = False, **kwargs: Any) -> Union[dict, Any, httpx.Response]:
        response = await self._send_request(method=method, endpoint=endpoint, raise_for_status=raise_for_status, **kwargs)
        if return_response:
            return response
        try:
            if self.response_model:
                parsed_response = response.json()
                return self.response_model.parse_obj(parsed_response)

            content_type = response.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                return response.json()
            elif 'text/' in content_type:
                return response.text
            else:
                return response.content
        except ValidationError as e:
            logger.error("Response validation failed", error=str(e))
            raise

    async def get(self, endpoint: str, **kwargs: Any) -> Union[dict, Any, httpx.Response]:
        """Send a GET request"""
        return await self.send_request(method="GET", endpoint=endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs: Any) -> Union[dict, Any, httpx.Response]:
        """Send a POST request"""
        return await self.send_request(method="POST", endpoint=endpoint, **kwargs)
