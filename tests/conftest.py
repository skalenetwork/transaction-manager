import os
import pathlib

import pytest
import redis
from skale.utils.account_tools import send_eth
from skale.wallets import RedisWalletAdapter, SgxWallet, Web3Wallet
from skale_core.settings import (
    SkaleSettings,
    write_internal_settings_file,
    write_node_settings_file,
)
from web3 import Web3

import transaction_manager.settings  # noqa: F401
from tests.utils.account import CERT_DIR, HOST_CONFIG_PATH
from transaction_manager.attempt_manager import (
    AttemptManagerV1,
    AttemptManagerV2,
    RedisAttemptStorage,
)
from transaction_manager.config import (
    ETH_PRIVATE_KEY,
    INTERNAL_SETTINGS_PATH,
    NODE_SETTINGS_PATH,
    get_node_settings,
)
from transaction_manager.eth import Eth
from transaction_manager.resources import w3 as gw3
from transaction_manager.txpool import TxPool
from transaction_manager.wallet import init_wallet


ETH_AMOUNT_FOR_TESTS = 3


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
def attempt_manager_v1(eth, attempt_storage, wallet):
    return AttemptManagerV1(eth, attempt_storage, wallet.address)


@pytest.fixture(autouse=True)
def settings():
    write_internal_settings_file(
        path=INTERNAL_SETTINGS_PATH,
        data={'node_type': 'skale', 'node_mode': 'active', 'skale_dir_host': './skale-data/'},
    )
    write_node_settings_file(
        path=NODE_SETTINGS_PATH,
        settings_type=SkaleSettings,
        data={
            'env_type': 'devnet',
            'endpoint': 'http://127.0.0.1:8545',
            'sgx_url': 'https://localhost:1026',
            'container_stop_timeout': 1,
            'tg_api_key': '123',
            'tg_chat_id': '-1231232',
            'node_version': '0.0.0',
            'block_device': '/dev/sda',
            'docker_lvmpy_version': '0.0.0',
            'manager_contracts': '0x0',
            'ima_contracts': '0x0',
        },
    )
    try:
        yield
    finally:
        pathlib.Path(INTERNAL_SETTINGS_PATH).unlink(missing_ok=True)
        pathlib.Path(NODE_SETTINGS_PATH).unlink(missing_ok=True)


@pytest.fixture
def w3() -> Web3:
    return gw3()


@pytest.fixture
def eth(w3):
    return Eth(w3)


@pytest.fixture
def w3wallet(w3):
    if not ETH_PRIVATE_KEY:
        return None
    return Web3Wallet(ETH_PRIVATE_KEY, w3)


@pytest.fixture
def wallet(w3, w3wallet):
    st = get_node_settings()
    if st.sgx_url:
        w = init_wallet(w3, config_filepath=HOST_CONFIG_PATH, path_to_cert=CERT_DIR)
    else:
        return w3wallet
    if isinstance(w, SgxWallet):
        send_eth(w3, w3wallet, w.address, ETH_AMOUNT_FOR_TESTS)
    return w


@pytest.fixture
def rdp(trs, w3wallet):
    """Redis wallet for base tests"""
    return RedisWalletAdapter(trs, 'test_pool', w3wallet)
