import logging

from skale.wallets import BaseWallet, SgxWallet, Web3Wallet  # type: ignore
from web3 import Web3

from .config import ETH_PRIVATE_KEY, SGX_URL
from .resources import w3 as gw3

logger = logging.getLogger(__name__)


class WalletInitializationError(Exception):
    pass


def init_wallet(w3: Web3 = gw3) -> BaseWallet:
    if SGX_URL:
        return SgxWallet(SGX_URL, w3)
    elif ETH_PRIVATE_KEY:
        return Web3Wallet(ETH_PRIVATE_KEY, w3)
    else:
        logger.warning('Both SGX_URL and ETH_PRIVATE_KEY was not provided')
        raise WalletInitializationError('Failed to initialize wallet')
