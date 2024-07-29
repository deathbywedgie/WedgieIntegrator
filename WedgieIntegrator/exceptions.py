from httpx import HTTPStatusError


class RateLimitError(HTTPStatusError): ...


class TemporaryRateLimitError(RateLimitError): ...
