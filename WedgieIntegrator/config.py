from pydantic import BaseModel
from typing import Optional

class APIConfig(BaseModel):
    """Configuration model for API client"""
    base_url: str
    api_key: Optional[str] = None
    oauth_token: Optional[str] = None
    retry_attempts: int = 3
    timeout: Optional[float] = 10.0  # Default timeout of 10 seconds
