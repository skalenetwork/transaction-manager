import os
import pytest
from skale import Skale
from skale.utils.web3_utils import init_web3

from configs import ENDPOINT
from nonce_manager import NonceManager
from tools.wallet import init_wallet


TEST_ABI_FILEPATH = os.getenv('TEST_ABI_FILEPATH')


@pytest.fixture
def wallet():
    web3 = init_web3(ENDPOINT)
    return init_wallet(web3)


@pytest.fixture
def skale(wallet):
    return Skale(ENDPOINT, TEST_ABI_FILEPATH, wallet)


@pytest.fixture
def nonce_manager(skale, wallet):
    nm = NonceManager(skale, wallet)
    yield nm
    nm.ensure_nonce()
