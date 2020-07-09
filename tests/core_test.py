import pytest

from skale import Skale
from skale.utils.web3_utils import init_web3, wait_for_receipt_by_blocks

from configs.web3 import ENDPOINT, ABI_FILEPATH
from core import sign_and_send
from nonce_manager import NonceManager
from tools.helper import init_wallet


TX_DICT = {
    'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
    'value': 9,
    'gas': 200000,
    'gasPrice': 1,
    'nonce': 7,
    'chainId': None,
    'data': '0x0'
}


@pytest.fixture
def wallet():
    web3 = init_web3(ENDPOINT)
    return init_wallet(web3)


@pytest.fixture
def skale(wallet):
    return Skale(ENDPOINT, ABI_FILEPATH, wallet)


@pytest.fixture
def nonce_manager(skale, wallet):
    nm = NonceManager(skale, wallet)
    return nm


def test_sign_and_send(wallet, skale, nonce_manager):
    tx = sign_and_send(TX_DICT, wallet, nonce_manager)
    wait_for_receipt_by_blocks(
        skale.web3,
        tx
    )
    assert isinstance(tx, str)


@pytest.fixture
def broken_wallet():
    class BrokenWallet:
        def sign_and_send(self, tx_dict):
            raise ValueError('nonce to low mock')
    return BrokenWallet()


def test_sign_and_send_broken_wallet(broken_wallet, skale, nonce_manager):
    with pytest.raises(ValueError):
        sign_and_send(TX_DICT, broken_wallet, nonce_manager)


def test_sign_and_send_concurrent(wallet, skale, nonce_manager):
    pass
