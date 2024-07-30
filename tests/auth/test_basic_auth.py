import os
import pytest
from WedgieIntegrator.config import APIConfig
from WedgieIntegrator.client import BaseAPIClient
from WedgieIntegrator.auth import BasicAuth

GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_PASSWORD = os.getenv('GITHUB_PASSWORD')
TEST_REPO_NAME = 'test-repo'

@pytest.fixture
def api_config():
    return APIConfig(base_url="https://api.github.com")

@pytest.fixture
def api_client(api_config):
    if not GITHUB_USERNAME or not GITHUB_PASSWORD:
        pytest.fail("Environment variables GITHUB_USERNAME and GITHUB_PASSWORD must be set")
    auth_strategy = BasicAuth(username=GITHUB_USERNAME, password=GITHUB_PASSWORD)
    return BaseAPIClient(config=api_config, auth_strategy=auth_strategy)

@pytest.mark.asyncio
async def test_get_authenticated_user(api_client):
    """Test GET request to retrieve authenticated user's details"""
    async with api_client:
        response_obj = await api_client.get(endpoint="/user")
        assert isinstance(response_obj.content, dict)
        assert 'login' in response_obj.content

@pytest.mark.asyncio
async def test_get_user_repos(api_client):
    """Test GET request to retrieve authenticated user's repositories"""
    async with api_client:
        response_obj = await api_client.get(endpoint="/user/repos")
        assert isinstance(response_obj.content, list)
        if response_obj.content:
            assert 'name' in response_obj.content[0]

@pytest.mark.asyncio
async def test_create_repo(api_client):
    """Test POST request to create a new repository"""
    repo_data = {
        'name': TEST_REPO_NAME,
        'description': 'This is a test repository',
        'private': False
    }
    async with api_client:
        response_obj = await api_client.post(endpoint="/user/repos", json=repo_data)
        assert isinstance(response_obj.content, dict)
        assert response_obj.content['name'] == TEST_REPO_NAME
        assert response_obj.content['description'] == 'This is a test repository'

@pytest.mark.asyncio
async def test_update_repo(api_client):
    """Test PATCH request to update an existing repository"""
    update_data = {
        'name': TEST_REPO_NAME,
        'description': 'This is an updated test repository',
        'private': False
    }
    async with api_client:
        response_obj = await api_client.send_request(method="PATCH", endpoint=f"/repos/{GITHUB_USERNAME}/{TEST_REPO_NAME}", json=update_data)
        assert isinstance(response_obj.content, dict)
        assert response_obj.content['description'] == 'This is an updated test repository'

@pytest.mark.asyncio
async def test_delete_repo(api_client):
    """Test DELETE request to delete a repository"""
    async with api_client:
        response_obj = await api_client.send_request(method="DELETE", endpoint=f"/repos/{GITHUB_USERNAME}/{TEST_REPO_NAME}")
        assert response_obj.response.status_code == 204  # No content
