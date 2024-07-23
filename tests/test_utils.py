import pytest
from WedgieIntegrator.utils import with_retries
from tenacity import RetryError

# ToDo Revisit this once I decide what I really want to offer with respect to retries

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
