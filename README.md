# WedgieIntegrator
WedgieIntegrator is an async friendly package for Python which acts as API client toolkit for creating and managing API clients with ease.

## Features

- Fully asynchronous
- Simple configuration
- Multiple authentication strategies
- Retry mechanisms
- Pagination
- Helpful logging

## Installation

```bash
pip install WedgieIntegrator
```

## Version History

### 0.1.3, 2024-08-09
A few fixes, and better support for pagination with a custom response object and/or POST requests

# ToDo
- Add pagination option where the response can provide all remaining links at once
- Add automatic wait & retry for rate limit errors (currently handled by integrations themselves)
- More tests
- Documentation
- sample scripts, or perhaps a library of specific API configurations

- kinda done: Add rate limiting (safe for Python 3.7)
