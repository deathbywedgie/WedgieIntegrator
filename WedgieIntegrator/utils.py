from tenacity import retry, stop_after_attempt, wait_exponential
from .response import APIResponse
from httpx import QueryParams
from .exceptions import ClientError

import logging
import structlog

_logger = logging.getLogger(__name__)
log = structlog.wrap_logger(_logger)


# ToDo Revisit this once I decide what I really want to offer with respect to retries
def with_retries(func):
    """Decorator to add retries to a function based on config"""
    def wrapper(self, *args, **kwargs):
        retry_decorator = retry(stop=stop_after_attempt(self.config.retry_attempts), wait=wait_exponential(min=1, max=10))
        decorated_func = retry_decorator(func)
        return decorated_func(self, *args, **kwargs)
    return wrapper


# ToDo In its current form, if the initial request contains a parameter like what page to start on, subsequent calls based on URL are still overwritten by that original param
#  This works as long as the request starts at the beginning, but if user requests from a specific starting point, it will just keep fetching that same list forever
def paginate_requests(func):
    """Decorator to handle pagination in API responses"""
    async def wrapper(self, *args, **kwargs):
        response_obj: APIResponse = await func(self, *args, **kwargs)
        if not response_obj.is_pagination:
            return response_obj
        result_limit = int(kwargs.get("result_limit") or 0)
        all_results = [r for r in response_obj.result_list or []]
        log.debug(
            "Paginated call recognized",
            url=str(response_obj.response.url),
            result_limit=result_limit or None,
            new_results=len(all_results),
        )

        all_responses = [response_obj]
        response_class = kwargs.pop("response_class", None)

        request_kwargs = QueryParams(kwargs)
        previous_calls = [request_kwargs]
        while True:
            if result_limit and len(all_results) >= result_limit:
                break
            pagination_payload = await response_obj.get_pagination_payload()
            if not pagination_payload:
                break
            request_kwargs = QueryParams(request_kwargs).merge(pagination_payload)
            if request_kwargs in previous_calls:
                log.fatal(
                    "Pagination failure: next call is the same as a previous call",
                    url=request_kwargs.get("endpoint"),
                    call_count=len(all_responses),
                    new_results=len(response_obj.result_list or []),
                    current_total=len(all_results),
                    result_limit=result_limit or None,
                )
                raise ClientError(f"Pagination failure: next call is the same as a previous call")
            previous_calls.append(request_kwargs)

            log.debug(
                "Continuing pagination",
                url=request_kwargs.get("endpoint"),
                result_limit=result_limit or None,
                current_result_count=len(all_results),
                current_call_count=len(all_responses),
            )
            response_obj = await func(self, *args, response_class=response_class, **request_kwargs)
            all_responses.append(response_obj)
            if response_obj.result_list:
                all_results.extend(response_obj.result_list)

        if result_limit:
            all_results = all_results[:result_limit]
        log.debug(
            "Pagination complete",
            url=request_kwargs.get("endpoint"),
            call_count=len(all_responses),
            result_count=len(all_results),
            result_limit=result_limit or None,
        )
        return all_responses, all_results
    return wrapper
