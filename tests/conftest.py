import json
from pathlib import Path

import pytest
import redis
from skale.wallets import RedisWalletAdapter, Web3Wallet
from web3 import Web3
from web3.contract import Contract

import transaction_manager.settings  # noqa: F401
from transaction_manager.attempt_manager import AttemptManagerV2, RedisAttemptStorage
from transaction_manager.config import ETH_PRIVATE_KEY
from transaction_manager.eth import Eth
from transaction_manager.resources import w3 as gw3
from transaction_manager.txpool import TxPool
from transaction_manager.wallet import init_wallet

TESTER_ARTIFACT = Path(__file__).parent / 'tester-contract' / 'Tester.json'


@pytest.fixture
def trs():
    r = redis.Redis()
    yield r
    r.flushdb()


@pytest.fixture
def tpool(trs):
    tp = TxPool('test_pool', trs)
    yield tp
    tp._clear()


@pytest.fixture
def attempt_storage(trs):
    return RedisAttemptStorage(trs)


@pytest.fixture
def attempt_manager(eth, attempt_storage, wallet):
    return AttemptManagerV2(eth, attempt_storage, wallet.address)


@pytest.fixture
def w3() -> Web3:
    return gw3()


@pytest.fixture
def eth(w3):
    return Eth(w3)


@pytest.fixture
def w3wallet(w3):
    return Web3Wallet(ETH_PRIVATE_KEY, w3)


@pytest.fixture
def wallet(w3):
    return init_wallet(w3)


@pytest.fixture(scope='session')
def tester() -> Contract:
    w3 = gw3()
    deployer = Web3Wallet(ETH_PRIVATE_KEY, w3)
    artifact = json.loads(TESTER_ARTIFACT.read_text())
    factory = w3.eth.contract(abi=artifact['abi'], bytecode=artifact['bytecode'])
    tx = factory.constructor().build_transaction(
        {'from': deployer.address, 'gasPrice': w3.eth.gas_price}
    )
    receipt = deployer.wait(deployer.sign_and_send(tx))
    return w3.eth.contract(address=receipt['contractAddress'], abi=artifact['abi'])


@pytest.fixture
def rdp(trs, w3wallet):
    """Redis wallet for base tests"""
    return RedisWalletAdapter(trs, 'test_pool', w3wallet)
