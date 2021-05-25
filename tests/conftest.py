import pytest
import redis

from skale.wallets import Web3Wallet

from transaction_manager.config import ETH_PRIVATE_KEY
from transaction_manager.eth import Eth
from transaction_manager.resources import w3 as gw3
from transaction_manager.txpool import TxPool

from tests.utils.sender import RedisSender


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
def sender(tpool, trs):
    return RedisSender(trs, tpool.name)


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

# import importlib
# import os
#
# import pytest
# from skale.utils.web3_utils import init_web3
#
# import config
# from configs.web3 import ENDPOINT
# from nonce_manager import NonceManager
# from tools.helper import init_wallet
#
#
# @pytest.fixture
# def wallet():
#     web3 = init_web3(ENDPOINT)
#     return init_wallet(web3)
#
#
# @pytest.fixture
# def nonce_manager(wallet):
#     web3 = init_web3(ENDPOINT)
#     nm = NonceManager(web3, wallet)
#     yield nm
#     nm.ensure_nonce()
#
#
# @pytest.fixture
# def disable_dry_run_env():
#     os.environ['DISABLE_DRY_RUN'] = 'True'
#     importlib.reload(config)
#     yield
#     os.environ.pop('DISABLE_DRY_RUN')
#     importlib.reload(config)
