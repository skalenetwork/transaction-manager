import redis

from .config import REDIS_URI

cpool = redis.ConnectionPool.from_url(REDIS_URI)
rs = redis.Redis(connection_pool=cpool)
