import importlib
import os

import pytest
from skale.utils.web3_utils import init_web3

import config
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


@pytest.fixture
def disable_dry_run_env():
    os.environ['DISABLE_DRY_RUN'] = 'True'
    importlib.reload(config)
    yield
    os.environ.pop('DISABLE_DRY_RUN')
    importlib.reload(config)
