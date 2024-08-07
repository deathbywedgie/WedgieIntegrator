from tenacity import retry, stop_after_attempt, wait_exponential
from .response import APIResponse

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
        log.debug("Pagination detected", url=str(response_obj.response.url))
        result_limit = kwargs.pop("result_limit", 0)
        all_responses = [response_obj]
        all_results = [r for r in response_obj.result_list or []]
        urls_fetched = []
        pagination_payload = await response_obj.get_pagination_payload()
        while pagination_payload:
            if result_limit and len(all_results) >= result_limit:
                break
            kwargs.update(pagination_payload)
            next_url = kwargs.get("endpoint")
            if next_url in urls_fetched:
                raise Exception(f"Next URL is the same as one previously requested already. URL: {next_url}")
            if response_obj.response.request.method == "GET":
                urls_fetched.append(next_url)
            log.debug("Continuing pagination", url=next_url)
            response_obj = await func(self, *args, **kwargs)
            all_responses.append(response_obj)
            if response_obj.result_list:
                all_results.extend(response_obj.result_list)
            pagination_payload = await response_obj.get_pagination_payload()

        if result_limit:
            return all_responses, all_results[:result_limit]
        return all_responses, all_results
    return wrapper
