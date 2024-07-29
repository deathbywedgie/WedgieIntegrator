from pydantic import BaseModel, ValidationError
import httpx
from tenacity import RetryError
from typing import Optional, Any, Type, Union
from .config import APIConfig
from .auth import AuthStrategy
from .exceptions import *
import asyncio

import logging
import structlog

# Configure logging
_logger = logging.getLogger(__name__)
log = structlog.wrap_logger(_logger)


class APIResponse:
    response: httpx.Response
    content: Union[dict, Any]
    content_type: str
    __content = None
    __content_type = None

    def __init__(self, api_client, response: httpx.Response):
        self.__client = api_client
        self.response = response

    @property
    def content_type(self):
        if self.__content_type is None:
            self.__content_type = self._parse_content_type(response=self.response)
        return self.__content_type

    @property
    def content(self):
        if self.__content is None:
            self.__content = self._parse_content(response=self.response)
        return self.__content

    @content.setter
    def content(self, value):
        self.__content = value

    @staticmethod
    def _parse_content_type(response: httpx.Response):
        return response.headers.get('Content-Type', '')

    def _parse_content(self, response: httpx.Response, response_model: Optional[Type[BaseModel]] = None):
        content_type = self._parse_content_type(response)
        if response_model:
            parsed_response = asyncio.run(asyncio.to_thread(response.json))
            return response_model.parse_obj(parsed_response)
        elif 'application/json' in content_type:
            return asyncio.run(asyncio.to_thread(response.json))
        elif 'text/' in content_type:
            return response.text
        else:
            return response.content


class BaseAPIClient:
    """Base class for API client"""
    VERBOSE = False

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

    @staticmethod
    def is_rate_limit_error(response: httpx.Response) -> bool:
        """Check if the response indicates a rate limit error"""
        return False

    @staticmethod
    def is_temporary_rate_limit_error(response: httpx.Response) -> bool:
        """Check if the response indicates a temporary rate limit error, which is not always applicable"""
        return False

    @staticmethod
    def is_pagination(response: httpx.Response) -> Optional[dict]:
        """Check if the response indicates pagination and return pagination information if available"""
        return None

    def continue_pagination(self, response: httpx.Response):
        """Parse pagination details and continue requests until all results are returned"""
        raise NotImplementedError("No default pagination method currently implemented")

    async def send_request(self, method: str, endpoint: str, raise_for_status=True, extract_content: bool = True, **kwargs) -> APIResponse:
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
            if self.is_pagination(response):
                return self.continue_pagination(response)
            return self.response_class(self, response)
        except ValidationError as e:
            log.error("Response validation failed", error=str(e), method=method, endpoint=endpoint)
            raise

    async def get(self, endpoint: str, **kwargs) -> Union[dict, Any, httpx.Response]:
        """Send a GET request"""
        return await self.send_request(method="GET", endpoint=endpoint, **kwargs)

    async def post(self, endpoint: str, **kwargs) -> Union[dict, Any, httpx.Response]:
        """Send a POST request"""
        return await self.send_request(method="POST", endpoint=endpoint, **kwargs)


class APIClient(BaseAPIClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def is_rate_limit_error(response: httpx.Response) -> bool:
        """Check if the response indicates a rate limit error"""
        return response.status_code == 429

    def is_pagination(self, response: httpx.Response) -> Optional[dict]:
        """Check if the response indicates pagination and return pagination information if available"""
        link_header = response.headers.get('Link')
        if link_header:
            links = {}
            for link in link_header.split(','):
                parts = link.split(';')
                url = parts[0].strip('<> ')
                rel = parts[1].strip().split('=')[1].strip('"')
                links[rel] = url
            return links
        return None

    def continue_pagination(self, response: httpx.Response):
        """Parse pagination details and continue requests until all results are returned"""
        raise NotImplementedError("No default pagination method currently implemented")
