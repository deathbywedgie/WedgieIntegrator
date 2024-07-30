from typing import Optional, Any, Type, Union

import httpx
from pydantic import BaseModel, ValidationError
from tenacity import RetryError

from .auth import AuthStrategy
from .config import APIConfig
from .exceptions import *
from .response import APIResponse

import logging
import structlog

# Configure logging
_logger = logging.getLogger(__name__)
log = structlog.wrap_logger(_logger)


class BaseAPIClient:
    """Base class for API client"""
    VERBOSE: bool = False
    is_failed: bool = False

    def __init__(self, config: APIConfig, auth_strategy: AuthStrategy, response_class: APIResponse = None, response_model: Optional[Type[BaseModel]] = None, verbose=False):
        if verbose is not None:
            self.VERBOSE = verbose
        self.config = config
        self.auth_strategy = auth_strategy
        self.response_class = response_class or APIResponse
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

    async def continue_request_pagination(self, response_obj: APIResponse, method: str, endpoint: str, **kwargs):
        """Parse pagination details and continue requests until all results are returned"""
        raise NotImplementedError("No default pagination method currently implemented")

    async def send_request(self, method: str, endpoint: str, raise_for_status=True, **kwargs) -> Union[httpx.Response, APIResponse, Any]:
        response_obj = await self._send_request(method=method, endpoint=endpoint, raise_for_status=raise_for_status, **kwargs)
        if response_obj.is_pagination:
            return await self.continue_request_pagination(response_obj, method=method, endpoint=endpoint, **kwargs)
        return response_obj

    async def _send_request(self, method: str, endpoint: str, raise_for_status=True, **kwargs) -> Union[httpx.Response, APIResponse, Any]:
        """Send an HTTP request with retries and authentication"""
        __logger = log.new(method=method, url=endpoint)
        if self.is_failed:
            __logger.fatal("Failure reported; aborting tasks")
            raise TaskAborted("Failure reported; aborting tasks")
        __logger.debug("Sending request")
        if self.client is None:
            raise RuntimeError("HTTP client is not initialized")

        request = self.client.build_request(method=method, url=endpoint, **kwargs)
        self.auth_strategy.authenticate(request)
        try:
            response = await self.client.send(request)
            self.log_verbose("Received response", status_code=response.status_code, logger=__logger)
            response_obj = self.response_class(api_client=self, response=response)
            if response_obj.is_rate_limit_error is True:
                raise RateLimitError("Rate limit error", request=request, response=response)
            if response_obj.is_rate_limit_failure is True:
                raise RateLimitFailure("Rate limit failure", request=request, response=response)
            if raise_for_status:
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            __logger.error("HTTP error occurred", status_code=e.response.status_code, content=e.response.text)
            raise
        except RetryError as e:
            __logger.error("Retry failed", error=str(e))
            raise
        except ValidationError as e:
            log.error("Response validation failed", error=str(e), method=method, url=endpoint)
            raise
        return response_obj

    async def get(self, endpoint: str, **kwargs) -> Union[dict, Any, httpx.Response]:
        """Send a GET request"""
        return await self.send_request(method="GET", endpoint=endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> Union[dict, Any, httpx.Response]:
        """Send a POST request"""
        return await self.send_request(method="POST", endpoint=endpoint, **kwargs)


class APIClient(BaseAPIClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def continue_request_pagination(self, response_obj: APIResponse, method: str, endpoint: str, **kwargs):
        """Parse pagination details and continue requests until all results are returned"""
        raise NotImplementedError("No default pagination method currently implemented")
