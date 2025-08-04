# ToDo
- add a way to get all pages at once
- add an "ignore_pagination" param for when the user wants to handle pagination themselves
- rename current "result_list" to something like "single_response_results"
- rename current "paginated_results" to "result_list" or something like "combined_results"
- consider getting rid of aiolimiter, because it contributes to package conflicts in SOAR (and I'm not using AsyncLimiter now anyway)
- define a request object that can be used to contain all request related configs and passed to the response object
- Add automatic wait & retry for rate limit errors (currently handled by integrations themselves)
- More tests
- Documentation
- sample scripts, or perhaps a library of specific API configurations

- kinda done: Add rate limiting (safe for Python 3.7)
