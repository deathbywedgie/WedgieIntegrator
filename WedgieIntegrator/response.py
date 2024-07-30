import asyncio
from typing import Optional, Any, Type, Union

import httpx
from pydantic import BaseModel


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
    additional_json_content_types: list = None 

    def __init__(self, api_client, response: httpx.Response, response_model: Optional[Type[BaseModel]] = None):
        self.response = response
        self.response_model = response_model
        self.content_type = response.headers.get('Content-Type', '')
        self.__client = api_client

    @property
    def content(self):
        return self.__content

    async def _async_pre_parsing(self):
        if self.__content is None:
            if self.response_model:
                parsed_response = await asyncio.to_thread(self.response.json)
                self.__content = self.response_model.parse_obj(parsed_response)
            elif 'application/json' in self.content_type:
                self.__content = await asyncio.to_thread(self.response.json)
            elif self.additional_json_content_types and self.content_type in self.additional_json_content_types:
                self.__content = await asyncio.to_thread(self.response.json)
            elif 'text/' in self.content_type:
                self.__content = self.response.text
            else:
                self.__content = self.response.content
        return self.__content


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
