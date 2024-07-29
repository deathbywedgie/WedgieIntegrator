from WedgieIntegrator.config import APIConfig

def test_api_config_defaults():
    config = APIConfig(base_url="https://example.com")
    assert config.base_url == "https://example.com"
    # assert config.retry_attempts == 3
    assert config.timeout == 10.0
    assert config.verify_ssl is True

def test_api_config_custom():
    config = APIConfig(base_url="https://example.com", timeout=20.0, verify_ssl=False)
    assert config.base_url == "https://example.com"
    # assert config.retry_attempts == 5
    assert config.timeout == 20.0
    assert config.verify_ssl is False
