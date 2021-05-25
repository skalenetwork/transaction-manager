import redis

from .config import ENDPOINT, REDIS_URI
from skale.utils.web3_utils import init_web3  # type: ignore

# TODO: IVD check out options to configure
cpool = redis.ConnectionPool.from_url(REDIS_URI)
rs = redis.Redis(connection_pool=cpool)
# TODO: IVD check out options to configure
w3 = init_web3(ENDPOINT)
