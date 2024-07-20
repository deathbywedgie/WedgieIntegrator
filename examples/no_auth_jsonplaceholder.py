import os
import asyncio
from wedgieintegrator import APIConfig, BaseAPIClient, NoAuth

# Load credentials from environment variables
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_PASSWORD = os.getenv('GITHUB_PASSWORD')

if not GITHUB_USERNAME or not GITHUB_PASSWORD:
    raise ValueError("Environment variables GITHUB_USERNAME and GITHUB_PASSWORD must be set")

# Configure the API client
api_config = APIConfig(base_url="https://jsonplaceholder.typicode.com", api_key=None, oauth_token=None)
auth_strategy = NoAuth()
api_client = BaseAPIClient(config=api_config, auth_strategy=auth_strategy)

async def get_all_posts():
    async with api_client:
        return await api_client.get(endpoint="/posts")

async def get_single_post():
    async with api_client:
        return await api_client.get(endpoint="/posts/1")

async def create_post(data_dict):
    async with api_client:
        return await api_client.post(endpoint="/posts", json=data_dict)

if __name__ == "__main__":
    results = asyncio.run(get_all_posts())
    result = asyncio.run(get_single_post())
    response = asyncio.run(create_post({
        'title': 'fooZ',
        'body': 'barZ',
        'userId': 1
    }))
