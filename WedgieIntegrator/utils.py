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
        first_response: APIResponse = await func(self, *args, **kwargs)
        if not first_response.is_pagination:
            return first_response
        result_limit = int(kwargs.get("result_limit") or 0)
        first_response.paginated_responses.append(first_response)
        log_params = dict(original_url=kwargs.get("endpoint"))
        if result_limit:
            log_params["result_limit"] = result_limit
        request_log = log.new(**log_params)
        request_log.debug(
            "Paginated call recognized",
            new_results=len(first_response.paginated_results),
        )

        # Track previous calls to detect duplicates, but must do it with copies
        previous_calls = [QueryParams(kwargs)]
        response_obj = first_response
        while True:
            if result_limit and len(first_response.paginated_results) >= result_limit:
                break
            pagination_payload = await response_obj.get_pagination_payload()
            if not pagination_payload:
                break
            kwargs.update(pagination_payload)
            # Must store copies, because kwargs is mutable and gets changed with each paginated call
            call_copy = QueryParams(kwargs)
            if call_copy in previous_calls:
                request_log.fatal(
                    "Pagination failure: next call is the same as a previous call",
                    url=kwargs.get("endpoint"),
                    call_count=len(first_response.paginated_responses),
                    new_results=len(response_obj.result_list or []),
                    result_count=len(first_response.paginated_results),
                )
                raise ClientError(f"Pagination failure: next call is the same as a previous call")
            previous_calls.append(call_copy)

            request_log.debug(
                "Continuing pagination",
                url=kwargs.get("endpoint"),
                call_count=len(first_response.paginated_responses),
                new_results=len(response_obj.result_list or []),
                result_count=len(first_response.paginated_results),
            )
            response_obj = await func(self, *args, **kwargs)
            first_response.paginated_responses.append(response_obj)

        request_log.debug(
            "Pagination complete",
            call_count=len(first_response.paginated_responses),
            result_count=len(first_response.paginated_results),
        )
        return first_response
    return wrapper
