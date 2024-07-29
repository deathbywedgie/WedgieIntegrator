from httpx import HTTPStatusError


class BaseClientException(BaseException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class RateLimitError(HTTPStatusError, BaseClientException): ...


class TemporaryRateLimitError(RateLimitError, BaseClientException): ...
