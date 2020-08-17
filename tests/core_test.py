import pytest
from mock import Mock

from sgx.http import SgxUnreachableError
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
    tx, error = sign_and_send(TX_DICT, wallet, nonce_manager)
    assert error is None
    wait_for_receipt_by_blocks(
        skale.web3,
        tx
    )
    assert isinstance(tx, str)


@pytest.fixture
def broken_wallet():
    bw_mock = Mock()
    bw_mock.sign_and_send = Mock(side_effect=ValueError('Nonce to low mock'))
    return bw_mock


def test_sign_and_send_broken_wallet(broken_wallet, skale, nonce_manager):
    tx, error = sign_and_send(TX_DICT, broken_wallet, nonce_manager)
    assert tx is None
    assert error == 'Nonce to low mock'
    assert broken_wallet.sign_and_send.call_count == 3


@pytest.fixture
def sgx_unreachable_wallet():
    sw_mock = Mock()
    sw_mock.sign_and_send = Mock(
        side_effect=SgxUnreachableError('sgx unreachable'))
    return sw_mock


def test_sign_and_send_sgx_broken_wallet(sgx_unreachable_wallet,
                                         skale, nonce_manager):
    tx, error = sign_and_send(TX_DICT, sgx_unreachable_wallet, nonce_manager)
    assert tx is None
    assert error == 'Sgx server is unreachable'
    assert sgx_unreachable_wallet.sign_and_send.call_count == 1
