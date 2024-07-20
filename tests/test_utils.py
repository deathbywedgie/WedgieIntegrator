import pytest
from wedgieintegrator.utils import with_retries
from tenacity import RetryError

class TestClient:
    def __init__(self):
        self.config = type('Config', (), {'retry_attempts': 3})

    @with_retries
    def unreliable_method(self):
        raise Exception("Temporary failure")

    @with_retries
    def reliable_method(self):
        return "Success"

def test_with_retries_success():
    client = TestClient()
    result = client.reliable_method()
    assert result == "Success"

def test_with_retries_failure():
    client = TestClient()
    with pytest.raises(RetryError):
        client.unreliable_method()
