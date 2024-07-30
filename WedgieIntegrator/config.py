from pydantic import BaseModel
from typing import Optional


class APIConfig(BaseModel):
    """Configuration model for API client"""
    base_url: str
    # ToDo Revisit this, and probably need to separate out retry types (connection, server errors, rate limits, etc.)
    # retry_attempts: int = 3
    timeout: Optional[float] = 10.0  # Default timeout of 10 seconds
    verify_ssl: bool = True
    requests_per_minute: int = None
