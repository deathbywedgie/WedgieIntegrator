import os
import asyncio
from WedgieIntegrator import APIConfig, BaseAPIClient, BasicAuth

# Load credentials from environment variables
GITHUB_USERNAME = os.getenv('GITHUB_USERNAME')
GITHUB_PASSWORD = os.getenv('GITHUB_PASSWORD')

if not GITHUB_USERNAME or not GITHUB_PASSWORD:
    raise ValueError("Environment variables GITHUB_USERNAME and GITHUB_PASSWORD must be set")

# Configure the API client
api_config = APIConfig(base_url="https://api.github.com")
auth_strategy = BasicAuth(username=GITHUB_USERNAME, password=GITHUB_PASSWORD)
api_client = BaseAPIClient(config=api_config, auth_strategy=auth_strategy)

async def list_private_repos():
    """List all private repositories for the authenticated user"""
    async with api_client:
        response = await api_client.get(endpoint="/user/repos", params={"visibility": "private"})
        if isinstance(response, list):
            for repo in response:
                print(f"Repo Name: {repo['name']}, Description: {repo.get('description', 'No description')}")
        else:
            print("Failed to retrieve repositories")

if __name__ == "__main__":
    asyncio.run(list_private_repos())
