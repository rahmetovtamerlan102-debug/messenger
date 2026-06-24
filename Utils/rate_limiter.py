from django_redis import get_redis_connection
import time

class DistributedRateLimiter:
    def __init__(self, key_prefix, limit, window):
        self.key_prefix = key_prefix
        self.limit = limit
        self.window = window
        self.redis = get_redis_connection("default")
        self.lua_script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local now = tonumber(ARGV[3])
            local window_start = now - window
            redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
            local count = redis.call('ZCARD', key)
            if count < limit then
                redis.call('ZADD', key, now, now)
                redis.call('EXPIRE', key, window)
                return 1
            else
                return 0
            end
        """
        self.script = self.redis.register_script(self.lua_script)

    def allow(self, identifier):
        key = f"{self.key_prefix}:{identifier}"
        now = int(time.time())
        result = self.script(keys=[key], args=[self.limit, self.window, now])
        return result == 1
