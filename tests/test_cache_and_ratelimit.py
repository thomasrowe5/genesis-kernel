import time

from genesis.router.cache import InMemoryCache
from genesis.router.rate_limit import RateLimitConfig, TokenBucketRateLimiter


def test_cache_round_trip():
    cache = InMemoryCache(default_ttl=10)
    key = cache.make_key("fib", (10,), {}, module="fib", version="v1")
    assert cache.get(key) is None
    cache.set(key, 55, ttl=1)
    assert cache.get(key).value == 55
    time.sleep(1.1)
    assert cache.get(key) is None


def test_rate_limiter_enforces_bucket():
    limiter = TokenBucketRateLimiter(RateLimitConfig(rate_per_sec=0, burst=2))
    assert limiter.allow("fib") is True
    assert limiter.allow("fib") is True
    assert limiter.allow("fib") is False
