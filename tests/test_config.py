from WedgieIntegrator.config import APIConfig

def test_api_config_defaults():
    config = APIConfig(base_url="https://example.com")
    assert config.base_url == "https://example.com"
    assert config.api_key is None
    assert config.oauth_token is None
    assert config.retry_attempts == 3
    assert config.timeout == 10.0

def test_api_config_custom():
    config = APIConfig(base_url="https://example.com", api_key="dummy_api_key", oauth_token="dummy_oauth_token", retry_attempts=5, timeout=20.0)
    assert config.base_url == "https://example.com"
    assert config.api_key == "dummy_api_key"
    assert config.oauth_token == "dummy_oauth_token"
    assert config.retry_attempts == 5
    assert config.timeout == 20.0
