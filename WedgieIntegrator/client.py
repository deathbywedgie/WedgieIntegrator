from typing import Optional, Any, Type, Union, Dict, List
import httpx
from pydantic import BaseModel, ValidationError
from tenacity import RetryError

from .auth import AuthStrategy, NoAuth
from .exceptions import RateLimitError, RateLimitFailure, TaskAborted
from .response import APIResponse
from .utils import paginate_requests

import logging
import structlog

# Configure logging
_logger = logging.getLogger(__name__)
log = structlog.wrap_logger(_logger)


class APIClient:
    """Base class for API client"""
    is_failed: bool = False

    base_url: str
    # ToDo Revisit this, and probably need to separate out retry types (connection, server errors, rate limits, etc.)
    # retry_attempts: int = 3
    timeout: Optional[float] = 10.0  # Default timeout of 10 seconds
    verify_ssl: bool = True
    # ToDo Future use
    requests_per_minute: int = None
    verbose: bool = False

    auth_strategy: Optional[AuthStrategy] = None
    response_class: Optional[Type[APIResponse]] = None
    response_model: Optional[Type[BaseModel]] = None

    def __init__(self,
                 base_url: str,
                 *,  # Force key-value pairs for input
                 auth_strategy: Optional[AuthStrategy] = None,
                 response_class: Optional[Type[APIResponse]] = None,
                 response_model: Optional[Type[BaseModel]] = None,
                 timeout: float = 10.0,
                 verify_ssl: bool = True,
                 requests_per_minute: int = None,
                 verbose: bool = False,
                 ):
        self.base_url = base_url
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.requests_per_minute = requests_per_minute
        self.verbose = verbose
        self.auth_strategy = auth_strategy or NoAuth()
        self.response_class = response_class or APIResponse
        self.response_model = response_model
        # Initialize client here
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout, verify=self.verify_ssl)

    async def __aenter__(self) -> 'APIClient':
        # No need to initialize the client here as it is already initialized in __init__
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[Any]):
        if self.client:
            await self.client.aclose()

    def log_verbose(self, msg, logger=None, **kwargs):
        if not logger:
            logger = log
        if self.verbose:
            logger.debug(msg, **kwargs)

    async def create_response_object(self, response: httpx.Response):
        response_obj = self.response_class(api_client=self, response=response, response_model=self.response_model)
        if response_obj.content is None:
            await response_obj._async_parse_content()
        return response_obj

    @paginate_requests
    async def send_request(self, method: str, endpoint: str, raise_for_status=True, result_limit: int = None, **kwargs) -> Union[httpx.Response, APIResponse, Dict, List, Any]:
        """Send an HTTP request with retries and authentication"""
        _ = result_limit  # Used only by pagination
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
            response_obj = await self.create_response_object(response=response)
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

    async def get(self, endpoint: str, **kwargs):
        """Send a GET request"""
        return await self.send_request(method="GET", endpoint=endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs):
        """Send a POST request"""
        return await self.send_request(method="POST", endpoint=endpoint, **kwargs)
