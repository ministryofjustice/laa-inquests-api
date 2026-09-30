from pyrate_limiter import Duration, Limiter, Rate

RATE_LIMIT_EXEMPT_PATHS = frozenset({"/", "/health"})

def create_rate_limiter(request_limit: int = 900, request_window_in_minutes: int = 15) -> Limiter:
    return Limiter(Rate(request_limit, Duration.MINUTE * request_window_in_minutes))
