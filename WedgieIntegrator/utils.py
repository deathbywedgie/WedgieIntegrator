from tenacity import retry, stop_after_attempt, wait_exponential
from .response import APIResponse

# ToDo Revisit this once I decide what I really want to offer with respect to retries

def with_retries(func):
    """Decorator to add retries to a function based on config"""
    def wrapper(self, *args, **kwargs):
        retry_decorator = retry(stop=stop_after_attempt(self.config.retry_attempts), wait=wait_exponential(min=1, max=10))
        decorated_func = retry_decorator(func)
        return decorated_func(self, *args, **kwargs)
    return wrapper


def paginate_requests(func):
    """Decorator to handle pagination in API responses"""
    async def wrapper(self, *args, **kwargs):
        response_obj: APIResponse = await func(self, *args, **kwargs)
        if not response_obj.is_pagination:
            return response_obj
        result_limit = kwargs.pop("result_limit", 0)
        all_results = []
        if response_obj.result_list:
            all_results.extend(response_obj.result_list)
        all_responses = [response_obj]
        next_url = response_obj.pagination_links.get("next")
        while next_url:
            if result_limit and len(all_results) >= result_limit:
                break
            kwargs['endpoint'] = next_url
            # if '?' in next_url and 'params' in kwargs:
            #     del kwargs['params']
            next_response = await func(self, *args, **kwargs)
            all_responses.append(next_response)
            if next_response.result_list:
                all_results.extend(next_response.result_list)
            next_url = next_response.pagination_links.get("next")

        if result_limit:
            return all_responses, all_results[:result_limit]
        return all_responses, all_results
    return wrapper
