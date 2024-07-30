from httpx import HTTPStatusError


class BaseClientException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class RateLimitError(HTTPStatusError, BaseClientException): ...


class RateLimitFailure(HTTPStatusError, BaseClientException): ...
