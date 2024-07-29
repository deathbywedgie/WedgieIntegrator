"""
For testing WedgieIntegrator with a no auth API
"""

import pytest
from WedgieIntegrator.config import APIConfig
from WedgieIntegrator.client import BaseAPIClient
from WedgieIntegrator.auth import NoAuth

# ToDo this was supposed to just test this package with a no auth API, but it turned into more comprehensive testing.
#  Revisit and rethink...

@pytest.fixture
def api_config():
    return APIConfig(base_url="https://jsonplaceholder.typicode.com", api_key=None, oauth_token=None)

@pytest.fixture
def api_client(api_config):
    auth_strategy = NoAuth()
    return BaseAPIClient(config=api_config, auth_strategy=auth_strategy)

@pytest.mark.asyncio
async def test_get_all_posts(api_client):
    """Test GET request to retrieve all posts"""
    async with api_client:
        response_obj = await api_client.get(endpoint="/posts")
        response = await response_obj.parse()
        assert isinstance(response, list)
        assert len(response) > 0
        assert 'id' in response[0]

@pytest.mark.asyncio
async def test_get_single_post(api_client):
    """Test GET request to retrieve a single post"""
    async with api_client:
        response_obj = await api_client.get(endpoint="/posts/1")
        response = await response_obj.parse()
        assert isinstance(response, dict)
        assert response['id'] == 1

@pytest.mark.asyncio
async def test_create_post(api_client):
    """Test POST request to create a new post"""
    post_data = {
        'title': 'foo',
        'body': 'bar',
        'userId': 1
    }
    async with api_client:
        response_obj = await api_client.post(endpoint="/posts", json=post_data)
        response = await response_obj.parse()
        assert isinstance(response, dict)
        assert response['title'] == 'foo'
        assert response['body'] == 'bar'
        assert response['userId'] == 1

@pytest.mark.asyncio
async def test_update_post(api_client):
    """Test PUT request to update an existing post"""
    update_data = {
        'id': 1,
        'title': 'foo',
        'body': 'bar',
        'userId': 1
    }
    async with api_client:
        response_obj = await api_client.send_request(method="PUT", endpoint="/posts/1", json=update_data)
        response = await response_obj.parse()
        assert isinstance(response, dict)
        assert response['title'] == 'foo'
        assert response['body'] == 'bar'

@pytest.mark.asyncio
async def test_delete_post(api_client):
    """Test DELETE request to delete a post"""
    async with api_client:
        response_obj = await api_client.send_request(method="DELETE", endpoint="/posts/1")
        response = await response_obj.parse()
        assert response == {}
