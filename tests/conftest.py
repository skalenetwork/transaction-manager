import pytest
from skale import Skale
from skale.utils.web3_utils import init_web3

from configs.web3 import ENDPOINT, ABI_FILEPATH
from nonce_manager import NonceManager
from tools.helper import init_wallet
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
