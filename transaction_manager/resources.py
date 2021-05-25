import redis

from .config import ENDPOINT, ETH_PRIVATE_KEY, REDIS_URI
from skale.utils.web3_utils import init_web3  # type: ignore
from skale.wallets import BaseWallet, Web3Wallet  # type: ignore
from web3 import Web3

# TODO: IVD check out options to configure
cpool: redis.ConnectionPool = redis.ConnectionPool.from_url(REDIS_URI)
rs: redis.Redis = redis.Redis(connection_pool=cpool)
# TODO: IVD check out options to configure
w3: Web3 = init_web3(ENDPOINT)

wallet: BaseWallet = Web3Wallet(ETH_PRIVATE_KEY, w3)
