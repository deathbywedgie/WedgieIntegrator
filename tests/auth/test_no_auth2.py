"""
For testing WedgieIntegrator with a no auth API
"""

import pytest
from WedgieIntegrator.config import APIConfig
from WedgieIntegrator.client import BaseAPIClient
from WedgieIntegrator.auth import NoAuth

@pytest.fixture
def api_config():
    # return APIConfig(base_url="https://jsonplaceholder.typicode.com", api_key=None, oauth_token=None)
    return APIConfig(base_url="https://httpbin.org", api_key=None, oauth_token=None)


@pytest.fixture
def api_client(api_config):
    auth_strategy = NoAuth()
    return BaseAPIClient(config=api_config, auth_strategy=auth_strategy)


@pytest.mark.asyncio
async def test_status_code_200(api_client):
    """Test GET request to retrieve a single post"""
    async with api_client:
        status_code = 200
        print(f"PRINTING /status/{status_code}")
        response = await api_client.get(endpoint=f"/status/{status_code}")
        print(type(response))
        assert isinstance(response, str)
        # assert isinstance(response, dict)
