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
    result_limit: int = None
    link_header: str = None
    _is_pagination: bool = None
    _content: Any = None
    _client = None

    def __init__(self, api_client, response: httpx.Response, response_model: Optional[Type[BaseModel]] = None, result_limit: int = None):
        self._client = api_client
        self.response = response
        self.response_model = response_model
        self.content_type = response.headers.get('Content-Type', '')
        if isinstance(result_limit, int) and result_limit > 0:
            self.result_limit = result_limit
        self._pagination_links = {}
        self._paginated_responses = []

    @property
    def is_pagination(self) -> bool:
        if self._is_pagination is not None:
            return self._is_pagination
        return False

    @is_pagination.setter
    def is_pagination(self, value):
        self._is_pagination = value

    @property
    def is_rate_limit_error(self):
        if self.response.status_code == 429:
            return True

    @property
    def is_rate_limit_failure(self):
        return False

    @property
    def content(self) -> Union[dict, list, Any]:
        # Remember that this is not accessible until after initialization, because _async_parse_content has to run first
        return self._content

    @content.setter
    def content(self, value):
        self._content = value

    @property
    def result_list(self):
        """Customizable property for returning results as a list, when applicable"""
        if isinstance(self.content, list):
            return self.content
        return []

    async def is_json(self):
        """Standalone parser to make customization easy"""
        if 'application/json' in self.content_type:
            return True
        return False

    @property
    def pagination_links(self) -> dict:
        # By making this a property, we ensure that it can't be overwritten, i.e. it always remains the same object
        # But it also makes it easier to override in subclasses
        return self._pagination_links

    @property
    def pagination_next_link(self):
        return self.pagination_links.get('next')

    async def get_pagination_payload(self):
        request_args = {}
        if self.pagination_next_link:
            request_args['endpoint'] = self.pagination_next_link
        return request_args

    async def _async_parse_content(self):
        if self.response_model:
            parsed_response = await to_thread(self.response.json)
            self._content = self.response_model.parse_obj(parsed_response)
        elif await self.is_json():
            self._content = await to_thread(self.response.json)
        elif 'text/' in self.content_type:
            self._content = self.response.text
        else:
            self._content = self.response.content

    @property
    def paginated_responses(self) -> list:
        # By making this a property, we ensure that it can't be overwritten, i.e. it always remains the same object
        # But it also makes it easier to override in subclasses
        return self._paginated_responses

    @property
    def paginated_results(self) -> list:
        if not isinstance(self.paginated_responses, list):
            return []
        return [result for response in self.paginated_responses for result in response.result_list][:self.result_limit]


class APIResponse(BaseAPIResponse):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.link_header = self.response.headers.get('Link')
        if self.link_header:
            for link in self.link_header.split(','):
                parts = link.split(';')
                url = parts[0].strip('<> ')
                rel = parts[1].strip().split('=')[1].strip('"')
                self.pagination_links[rel] = url
            if self.response.request.method == "GET":
                self.is_pagination = True
