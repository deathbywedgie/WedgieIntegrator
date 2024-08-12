from typing import Optional, Any, Type, Union, Dict, List
import httpx
from pydantic import BaseModel, ValidationError
from tenacity import RetryError
from aiolimiter import AsyncLimiter
import asyncio
from collections import deque
import time

from .auth import AuthStrategy, NoAuth
from .exceptions import RateLimitError, RateLimitFailure, TaskAborted
from .response import BaseAPIResponse
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
    timeout: Optional[float] = 10.0  # Default timeout of 10 seconds
    verify_ssl: bool = True
    requests_per_second: int = None
    requests_per_minute: int = None
    verbose: bool = False

    auth_strategy: Optional[AuthStrategy] = None
    response_class: Optional[Type[BaseAPIResponse]] = None
    response_model: Optional[Type[BaseModel]] = None
    limiter_per_second: Optional[AsyncLimiter] = None
    limiter_per_minute: Optional[AsyncLimiter] = None
    _request_timestamps: deque = deque()
    __max_requests_per_second: int = 0
    __total_requests: int = 0
    __total_retried_requests: int = 0

    # New attributes for retry configuration
    max_retries: int = 0  # Default to no retries
    max_retry_wait: float = 5.0  # Maximum wait time between retries in seconds

    def __init__(self,
                 base_url: str,
                 *,  # Force key-value pairs for input
                 auth_strategy: Optional[AuthStrategy] = None,
                 response_class: Optional[Type[BaseAPIResponse]] = None,
                 response_model: Optional[Type[BaseModel]] = None,
                 timeout: float = 10.0,
                 default_params: dict = None,
                 default_headers: dict = None,
                 verify_ssl: bool = True,
                 requests_per_minute: int = None,
                 requests_per_second: int = None,
                 verbose: bool = False,
                 max_retries: int = 0,
                 max_retry_wait: float = 5.0,
                 httpx_kwargs: dict = None,
                 ):
        self.base_url = base_url
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_second
        self.verbose = verbose
        self.auth_strategy = auth_strategy or NoAuth()
        self.response_class = response_class or BaseAPIResponse
        self.response_model = response_model
        self.max_retries = max_retries
        self.max_retry_wait = max_retry_wait
        # Initialize client here
        client_params = dict(base_url=self.base_url, timeout=self.timeout, verify=self.verify_ssl)
        if default_params:
            client_params["params"] = default_params
        if default_headers:
            client_params["headers"] = default_headers
        if httpx_kwargs:
            client_params.update(httpx_kwargs)
        self.client = httpx.AsyncClient(**client_params)

        # Initialize rate limiters
        if self.requests_per_second:
            self.limiter_per_second = AsyncLimiter(self.requests_per_second, time_period=1)
        if self.requests_per_minute:
            self.limiter_per_minute = AsyncLimiter(self.requests_per_minute, time_period=60)

    async def __aenter__(self) -> 'APIClient':
        # No need to initialize the client here as it is already initialized in __init__
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[Any]):
        if self.client:
            await self.client.aclose()

    @property
    def max_requests_per_second(self) -> int:
        """Returns the highest rate of requests per second reached."""
        return self.__max_requests_per_second

    @property
    def total_requests(self) -> int:
        """Returns the highest rate of requests per second reached."""
        return self.__total_requests

    @property
    def total_retried_requests(self):
        return self.__total_retried_requests

    def log_verbose(self, msg, logger=None, **kwargs):
        if not logger:
            logger = log
        if self.verbose:
            logger.debug(msg, **kwargs)

    async def create_response_object(self, response: httpx.Response, response_class: Optional[Type[BaseAPIResponse]], result_limit: int):
        response_class = response_class or self.response_class
        response_obj = response_class(api_client=self, response=response, response_model=self.response_model, result_limit=result_limit)
        if response_obj.content is None:
            await response_obj._async_parse_content()
        return response_obj

    async def _perform_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Helper function to send the HTTP request."""
        request = self.client.build_request(method=method, url=endpoint, **kwargs)
        self.auth_strategy.authenticate(request)
        return await self.client.send(request)

    async def _handle_response(self, response: httpx.Response, request: httpx.Request, response_class: Optional[Type[BaseAPIResponse]], result_limit: int) -> BaseAPIResponse:
        """Process the response and handle errors."""
        response_obj = await self.create_response_object(response=response, response_class=response_class, result_limit=result_limit)
        if response_obj.is_rate_limit_error:
            raise RateLimitError("Rate limit error", request=request, response=response)
        if response_obj.is_rate_limit_failure:
            raise RateLimitFailure("Rate limit failure", request=request, response=response)
        return response_obj

    @paginate_requests
    async def send_request(self, method: str, endpoint: str, raise_for_status=True, result_limit: int = None, response_class: Optional[Type[BaseAPIResponse]] = None, **kwargs) -> Union[httpx.Response, BaseAPIResponse, Dict, List, Any]:
        """Send an HTTP request with retries and authentication"""
        _ = result_limit  # Used only by pagination
        __logger = log.new(method=method, url=endpoint)
        if self.is_failed:
            __logger.fatal("Failure reported; aborting tasks")
            raise TaskAborted("Failure reported; aborting tasks")
        __logger.debug("Sending request")
        if self.client is None:
            raise RuntimeError("HTTP client is not initialized")

        self.__total_requests += 1
        retries = 0
        while retries <= self.max_retries:
            try:
                # Apply both rate limiters
                if self.limiter_per_second and self.limiter_per_minute:
                    async with self.limiter_per_second, self.limiter_per_minute:
                        response = await self._perform_request(method, endpoint, **kwargs)
                elif self.limiter_per_second:
                    async with self.limiter_per_second:
                        response = await self._perform_request(method, endpoint, **kwargs)
                elif self.limiter_per_minute:
                    async with self.limiter_per_minute:
                        response = await self._perform_request(method, endpoint, **kwargs)
                else:
                    response = await self._perform_request(method, endpoint, **kwargs)

                # Log the request time
                current_time = time.time()
                self._request_timestamps.append(current_time)
                # Remove timestamps older than 1 second
                while self._request_timestamps and self._request_timestamps[0] < current_time - 1:
                    self._request_timestamps.popleft()
                # Update the max requests per second
                current_rate = len(self._request_timestamps)
                if current_rate > self.__max_requests_per_second:
                    self.__max_requests_per_second = current_rate

                self.log_verbose("Received response", status_code=response.status_code, logger=__logger)
                response_obj = await self._handle_response(response=response, request=response.request, response_class=response_class, result_limit=result_limit)
                if raise_for_status:
                    response.raise_for_status()
                return response_obj
            except httpx.TransportError as e:  # Retry only on connection errors for now
                retries += 1
                if retries > self.max_retries:
                    if self.max_retries > 0:
                        __logger.error(f"Exceeded maximum retries ({self.max_retries})")
                    raise
                self.__total_retried_requests += 1
                __logger.warning(f"Connection error occurred: {e}. Retry {retries}/{self.max_retries}.")
                # Exponential backoff with a max wait time
                retry_wait = min(2 ** retries, self.max_retry_wait)
                await asyncio.sleep(retry_wait)

    async def get(self, endpoint: str, **kwargs):
        """Send a GET request"""
        return await self.send_request(method="GET", endpoint=endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs):
        """Send a POST request"""
        return await self.send_request(method="POST", endpoint=endpoint, **kwargs)
