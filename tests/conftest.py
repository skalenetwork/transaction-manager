import os

import pytest
from skale.utils.web3_utils import init_web3

from configs.web3 import ENDPOINT
from tools.helper import init_web3_wallet


@pytest.fixture
def web3():
    return init_web3(ENDPOINT)


@pytest.fixture
def wallet(web3):
    pk_file = os.getenv('PK_FILE')
    return init_web3_wallet(web3, pk_file)
