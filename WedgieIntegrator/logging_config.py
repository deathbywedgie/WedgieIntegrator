import structlog
from logging import getLevelName

def configure_structlog(log_level="WARNING"):
    """Configure structlog if it has not been configured by the user"""
    if not structlog.is_configured():
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer()
            ],
            wrapper_class=structlog.make_filtering_bound_logger(getLevelName(log_level))
        )
