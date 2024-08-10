from typing import Optional, Any, Type, Union

import httpx
from pydantic import BaseModel
try:
    from asyncio import to_thread
except ImportError:
    from .asyncio_workaround import to_thread


class BaseAPIResponse:
    response: httpx.Response
    response_model: Optional[Type[BaseModel]] = None
    content_type: str
    is_rate_limit_error: bool = False
    is_rate_limit_failure: bool = False
    is_pagination: bool = False
    link_header: str = None
    pagination_links: dict = None
    __content = None
    _client = None

    def __init__(self, api_client, response: httpx.Response, response_model: Optional[Type[BaseModel]] = None):
        self._client = api_client
        self.response = response
        self.response_model = response_model
        self.content_type = response.headers.get('Content-Type', '')
        if self.response.status_code == 429:
            self.is_rate_limit_error = True

    @property
    def content(self) -> Union[dict, list, Any]:
        # Remember that this is not accessible until after initialization, because _async_parse_content has to run first
        return self.__content

    @property
    def result_list(self):
        """Customizable property for returning results as a list, when applicable"""
        if isinstance(self.content, list):
            return self.content

    async def is_json(self):
        """Standalone parser to make customization easy"""
        if 'application/json' in self.content_type:
            return True
        return False

    @property
    def pagination_next_link(self):
        if self.pagination_links:
            return self.pagination_links.get('next')

    async def get_pagination_payload(self):
        request_args = {}
        if self.pagination_next_link:
            request_args['endpoint'] = self.pagination_next_link
        return request_args

    async def _async_parse_content(self):
        if self.response_model:
            parsed_response = await to_thread(self.response.json)
            self.__content = self.response_model.parse_obj(parsed_response)
        elif await self.is_json():
            self.__content = await to_thread(self.response.json)
        elif 'text/' in self.content_type:
            self.__content = self.response.text
        else:
            self.__content = self.response.content


class APIResponse(BaseAPIResponse):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.link_header = self.response.headers.get('Link')
        if self.link_header:
            self.pagination_links = {}
            for link in self.link_header.split(','):
                parts = link.split(';')
                url = parts[0].strip('<> ')
                rel = parts[1].strip().split('=')[1].strip('"')
                self.pagination_links[rel] = url
            if self.response.request.method == "GET":
                self.is_pagination = True
