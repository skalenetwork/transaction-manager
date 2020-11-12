import pytest
from skale.utils.web3_utils import init_web3

from configs.web3 import ENDPOINT
from nonce_manager import NonceManager
from tools.helper import init_wallet


@pytest.fixture
def wallet():
    web3 = init_web3(ENDPOINT)
    return init_wallet(web3)


@pytest.fixture
def nonce_manager(wallet):
    web3 = init_web3(ENDPOINT)
    nm = NonceManager(web3, wallet)
    yield nm
    nm.ensure_nonce()
