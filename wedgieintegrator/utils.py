from tenacity import retry, stop_after_attempt, wait_exponential

# ToDo Revisit this once I decide what I really want to offer with respect to retries

def with_retries(func):
    """Decorator to add retries to a function based on config"""
    def wrapper(self, *args, **kwargs):
        retry_decorator = retry(stop=stop_after_attempt(self.config.retry_attempts), wait=wait_exponential(min=1, max=10))
        decorated_func = retry_decorator(func)
        return decorated_func(self, *args, **kwargs)
    return wrapper
