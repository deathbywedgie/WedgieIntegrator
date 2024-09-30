from typing import Optional, Any, Type, Union, Dict
import httpx
# ToDo Fix type hints so this can be removed from requirements
from pydantic import BaseModel
# from aiolimiter import AsyncLimiter
import asyncio
from collections import deque
import time
from dataclasses import dataclass, field

from .auth import AuthStrategy, NoAuth
from .exceptions import RateLimitError, RateLimitFailure, TaskAborted
from .response import BaseAPIResponse
from .utils import paginate_requests

import logging
import structlog

# Configure logging
_logger = logging.getLogger(__name__)
log = structlog.wrap_logger(_logger)


@dataclass
class APIConfig:
    base_url: str = None
    timeout: float = 10.0
    verify_ssl: bool = True
    default_params: Optional[Dict] = None
    default_headers: Optional[Dict] = None
    httpx_kwargs: Optional[Dict] = None
    client: httpx.AsyncClient = field(init=False)
    verbose: bool = False

    @property
    def client_params(self):
        client_params = {
            "base_url": self.base_url,
            "timeout": self.timeout,
            "verify": self.verify_ssl,
            "params": self.default_params,
            "headers": self.default_headers,
        }
        client_params = {k: v for k, v in client_params.items() if v is not None}
        client_params.update(self.httpx_kwargs)
        return client_params

    def __post_init__(self):
        self.httpx_kwargs = self.httpx_kwargs or {}
        self.client = httpx.AsyncClient(**self.client_params)

    async def reinit_web_client(self):
        if self.client is not None:
            try:
                await self.client.aclose()
            except RuntimeError:
                pass
        self.client = httpx.AsyncClient(**self.client_params)


class APIClient:
    """Base class for API client"""
    # requests_per_second: int = None
    # requests_per_minute: int = None
    auth_strategy: Optional[AuthStrategy] = None
    response_class: Optional[Type[BaseAPIResponse]] = None
    response_model: Optional[Type[BaseModel]] = None
    # limiter_per_second: Optional[AsyncLimiter] = None
    # limiter_per_minute: Optional[AsyncLimiter] = None
    __max_requests_per_second: int = 0
    __total_requests: int = 0
    __total_retried_requests: int = 0

    # New attributes for retry configuration
    max_retries: int = 0  # Default to no retries
    max_retry_wait: float = 5.0  # Maximum wait time between retries in seconds

    def __init__(self,
                 *,  # Force key-value pairs for input
                 auth_strategy: Optional[AuthStrategy] = None,
                 config: Optional[Type[APIConfig]] = None,
                 response_class: Optional[Type[BaseAPIResponse]] = None,
                 response_model: Optional[Type[BaseModel]] = None,
                 base_url: str = None,
                 timeout: float = 10.0,
                 default_params: dict = None,
                 default_headers: dict = None,
                 verify_ssl: bool = True,
                 verbose: bool = False,
                 max_retries: int = 0,
                 max_retry_wait: float = 5.0,
                 httpx_kwargs: dict = None,
                 ):
        self.is_failed: bool = False
        self._request_timestamps: deque = deque()

        # self.requests_per_minute = requests_per_minute
        # self.requests_per_second = requests_per_second
        self.auth_strategy = auth_strategy or NoAuth()
        self.config = config or APIConfig(
                base_url=base_url, timeout=timeout, verify_ssl=verify_ssl, default_params=default_params,
                default_headers=default_headers, httpx_kwargs=httpx_kwargs, verbose=verbose)
        self.response_class = response_class or BaseAPIResponse
        self.response_model = response_model
        self.max_retries = max_retries
        self.max_retry_wait = max_retry_wait

        # # Initialize rate limiters
        # if self.requests_per_second:
        #     self.limiter_per_second = AsyncLimiter(self.requests_per_second, time_period=1)
        # if self.requests_per_minute:
        #     self.limiter_per_minute = AsyncLimiter(self.requests_per_minute, time_period=60)

    async def __aenter__(self) -> 'APIClient':
        # No need to initialize the client here as it is already initialized in __init__
        return self

    async def __aexit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[Any]):
        if self.config.client:
            await self.config.client.aclose()

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
        if self.config.verbose:
            logger.debug(msg, **kwargs)

    async def create_response_object(self, response: httpx.Response, response_class: Optional[Type[BaseAPIResponse]], result_limit: int):
        response_class = response_class or self.response_class
        response_obj = response_class(api_client=self, response=response, response_model=self.response_model, result_limit=result_limit)
        if response_obj.content is None:
            await response_obj.async_parse_content()
        return response_obj

    async def _perform_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Helper function to send the HTTP request."""
        request = self.config.client.build_request(method=method, url=endpoint, **kwargs)
        self.auth_strategy.authenticate(request)
        try:
            return await self.config.client.send(request)
        except RuntimeError as e:
            if 'Event loop is closed' in str(e):
                log.warn("Event loop is closed; reinitializing the web client")
                await self.config.reinit_web_client()
                return await self.config.client.send(request)
            raise

    async def _handle_response(self, response: httpx.Response, request: httpx.Request, response_class: Optional[Type[BaseAPIResponse]], result_limit: int) -> BaseAPIResponse:
        """Process the response and handle errors."""
        response_obj = await self.create_response_object(response=response, response_class=response_class, result_limit=result_limit)
        if response_obj.is_rate_limit_error:
            raise RateLimitError("Rate limit error", request=request, response=response)
        if response_obj.is_rate_limit_failure:
            raise RateLimitFailure("Rate limit failure", request=request, response=response)
        return response_obj

    @paginate_requests
    async def send_request(self, method: str, endpoint: str, raise_for_status=True, result_limit: int = None, ignore_pagination=False, response_class: Optional[Type[BaseAPIResponse]] = None, **kwargs) -> Union[BaseAPIResponse, Any]:
        """
        Send an HTTP request with optional retries, pagination, and authentication.

        Args:
            method (str): HTTP method to use for the request (e.g., 'GET', 'POST')
            endpoint (str): The API endpoint (or other URL) to which you want to send the request.
            raise_for_status (bool, optional): Whether to raise an exception for HTTP error responses. Defaults to True.
            result_limit (int, optional): Limit the number of results for paginated responses. Defaults to None.
            ignore_pagination (bool, optional): Whether to ignore pagination and return only the first page of results. Defaults to False.
            response_class (Optional[Type[BaseAPIResponse]], optional): Custom response class to use for handling the response. Defaults to None.
            **kwargs: Additional arguments to pass to the httpx request.

        Returns:
            Union[BaseAPIResponse, Any]: The response object, which is BaseAPIResponse or a custom response class instance

        Raises:
            TaskAborted: If the client is in a failed state and cannot send requests.
            RuntimeError: If the HTTP client is not initialized.
            httpx.HTTPStatusError: If the response status code is an error and raise_for_status is True.
            httpx.TransportError: If a connection error occurs and the maximum number of retries is exceeded.
        """

        # Arguments used only by the pagination decorator
        _ = result_limit
        _ = ignore_pagination

        __logger = log.new(method=method, url=endpoint)
        if self.is_failed:
            __logger.fatal("Failure reported; aborting tasks")
            raise TaskAborted("Failure reported; aborting tasks")
        __logger.debug("Sending request")
        if self.config.client is None:
            raise RuntimeError("HTTP client is not initialized")

        self.__total_requests += 1
        retries = 0
        while retries <= self.max_retries:
            try:
                # # Apply both rate limiters
                # if self.limiter_per_second and self.limiter_per_minute:
                #     async with self.limiter_per_second, self.limiter_per_minute:
                #         response = await self._perform_request(method, endpoint, **kwargs)
                # elif self.limiter_per_second:
                #     async with self.limiter_per_second:
                #         response = await self._perform_request(method, endpoint, **kwargs)
                # elif self.limiter_per_minute:
                #     async with self.limiter_per_minute:
                #         response = await self._perform_request(method, endpoint, **kwargs)
                # else:
                #     response = await self._perform_request(method, endpoint, **kwargs)

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
