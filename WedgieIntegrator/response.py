from typing import Optional, Any, Type, Union

import httpx
from pydantic import BaseModel
try:
    from asyncio import to_thread
except ImportError:
    from _asyncio import to_thread


class BaseAPIResponse:
    response: httpx.Response
    response_model: Optional[Type[BaseModel]] = None
    content: Union[dict, Any]
    content_type: str
    is_rate_limit_error: bool = False
    is_rate_limit_failure: bool = False
    is_pagination: bool = False
    pagination_links: dict = None
    __content = None

    def __init__(self, api_client, response: httpx.Response, response_model: Optional[Type[BaseModel]] = None):
        self.response = response
        self.response_model = response_model
        self.content_type = response.headers.get('Content-Type', '')
        self.__client = api_client

    @property
    def content(self):
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
        if self.response.status_code == 429:
            self.is_rate_limit_error = True

        self.link_header = self.response.headers.get('Link')
        if self.link_header:
            self.is_pagination = True
            self.pagination_links = {}
            for link in self.link_header.split(','):
                parts = link.split(';')
                url = parts[0].strip('<> ')
                rel = parts[1].strip().split('=')[1].strip('"')
                self.pagination_links[rel] = url
