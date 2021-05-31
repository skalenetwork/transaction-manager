import pytest
import redis

from skale.wallets import Web3Wallet

from transaction_manager.config import ETH_PRIVATE_KEY
from transaction_manager.eth import Eth
from transaction_manager.resources import w3 as gw3
from transaction_manager.txpool import TxPool


@pytest.fixture
def trs():
    r = redis.Redis()
    yield r
    r.flushdb()


@pytest.fixture
def tpool(trs):
    tp = TxPool('test_pool', trs)
    yield tp
    tp.clear()


@pytest.fixture
def w3():
    return gw3


@pytest.fixture
def eth(w3):
    return Eth(w3)


@pytest.fixture
def w3wallet(w3):
    if not ETH_PRIVATE_KEY:
        return None
    return Web3Wallet(ETH_PRIVATE_KEY, w3)
