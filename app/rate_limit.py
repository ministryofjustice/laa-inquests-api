from pyrate_limiter import Duration, Limiter, Rate

RATE_LIMIT_EXEMPT_PATHS = frozenset({"/", "/health"})
RATE_LIMIT_RETRY_AFTER_SECONDS = 60


def create_rate_limiter(requests_per_minute: int = 2) -> Limiter:
    return Limiter(Rate(requests_per_minute, Duration.MINUTE))
