from pyrate_limiter import Duration, Limiter, Rate

def create_rate_limiter(
    request_limit, request_window_in_minutes
) -> Limiter:
    return Limiter(Rate(request_limit, Duration.MINUTE * request_window_in_minutes))
