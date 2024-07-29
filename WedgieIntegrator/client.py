from pydantic import BaseModel, ValidationError
import httpx
from tenacity import RetryError
from typing import Optional, Any, Type, Union
from .config import APIConfig
from .auth import AuthStrategy
from .exceptions import *

import logging
import structlog

# Configure logging
_logger = logging.getLogger(__name__)
log = structlog.wrap_logger(_logger)

class BaseAPIClient:
    """Base class for API client"""
    VERBOSE = False

    def __init__(self, config: APIConfig, auth_strategy: AuthStrategy, response_model: Optional[Type[BaseModel]] = None, verbose=False):
        if verbose is not None:
            self.VERBOSE = verbose
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

    def log_verbose(self, msg, logger=None, **kwargs):
        if not logger:
            logger = log
        if self.VERBOSE:
            logger.debug(msg, **kwargs)

    def is_rate_limit_error(self, response: httpx.Response) -> bool:
        """Check if the response indicates a rate limit error"""
        return response.status_code == 429

    def is_temporary_rate_limit_error(self, response: httpx.Response) -> bool:
        """
        Check if the response indicates a temporary rate limit error, which is not always applicable
        """
        return False

    async def send_request(self, method: str, endpoint: str, raise_for_status=True, extract_content: bool = True, **kwargs: Any):
        """Send an HTTP request with retries and authentication"""
        __logger = log.new(method=method, endpoint=endpoint)
        __logger.debug("Sending request", params=kwargs)
        if self.client is None:
            raise RuntimeError("HTTP client is not initialized")

        request = self.client.build_request(method=method, url=endpoint, **kwargs)
        self.auth_strategy.authenticate(request)
        try:
            response = await self.client.send(request)
            self.log_verbose("Received response", status_code=response.status_code, logger=__logger)
            if self.is_rate_limit_error(response) is True:
                raise RateLimitError("Rate limit error", request=request, response=response)
            if self.is_temporary_rate_limit_error(response) is True:
                raise RateLimitError("Temporary rate limit error", request=request, response=response)
            if raise_for_status:
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            __logger.error("HTTP error occurred", status_code=e.response.status_code, content=e.response.text)
            raise
        except RetryError as e:
            __logger.error("Retry failed", error=str(e))
            raise
        if not extract_content:
            return response
        try:
            content_type = response.headers.get('Content-Type', '')
            if self.response_model:
                parsed_response = response.json()
                content = self.response_model.parse_obj(parsed_response)
            elif 'application/json' in content_type:
                content = response.json()
            elif 'text/' in content_type:
                content = response.text
            else:
                content = response.content
        except ValidationError as e:
            log.error("Response validation failed", error=str(e), method=method, endpoint=endpoint)
            raise
        return response, content

    async def get(self, endpoint: str, **kwargs: Any) -> Union[dict, Any, httpx.Response]:
        """Send a GET request"""
        return await self.send_request(method="GET", endpoint=endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs: Any) -> Union[dict, Any, httpx.Response]:
        """Send a POST request"""
        return await self.send_request(method="POST", endpoint=endpoint, **kwargs)
