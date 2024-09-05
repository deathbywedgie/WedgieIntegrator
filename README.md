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

### 0.1.4, 2024-08-26
- Breaking change: will no longer return a different number of object (tuple vs single object) when pagination is detected.
- From now on, a single object will always be returned. When pagination is used, two new properties become useful:
  - "paginated_responses" is a combined list of all responses, from first to last
  - "paginated_results" is a combined list of all results from all paginated responses

### 0.1.4.1, 2024-08-28
Fix: new pagination fields must be exposed in order to work correctly in a subclass

### 0.1.4.2, 2024-08-30
- Fix: stop pagination if a response returns no results, no matter what the response object says
- Removed aiolimiter from the package and replaced with a NotImplementedError. Per second and per minute limits are not
 precise enough, so I do not yet use them, and I discovered that aiolimiter causes some conflicts, so I'll come back when I can move on from 3.7.

### 0.1.4.3, 2024-09-04
Fix: reinitialize the web client in the event of "Event loop is closed" runtime errors
