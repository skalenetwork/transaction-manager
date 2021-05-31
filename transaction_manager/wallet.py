import logging
import os

from skale.wallets import BaseWallet, SgxWallet, Web3Wallet  # type: ignore
from web3 import Web3

from .config import ETH_PRIVATE_KEY, NODE_DATA_PATH, SGX_URL
from .node import get_sgx_keyname
from .resources import w3 as gw3

logger = logging.getLogger(__name__)

PATH_TO_SGX_CERT = os.path.join(NODE_DATA_PATH, 'sgx_cert')


class WalletInitializationError(Exception):
    pass


def init_wallet(w3: Web3 = gw3) -> BaseWallet:
    wallet = None
    if ETH_PRIVATE_KEY:
        logger.info('Initializing web3 Wallet ...')
        wallet = Web3Wallet(ETH_PRIVATE_KEY, w3)
    elif SGX_URL:
        logger.info('Initializing sgx wallet ...')
        keyname = get_sgx_keyname()
        wallet = SgxWallet(
            SGX_URL,
            w3,
            key_name=keyname,
            path_to_cert=PATH_TO_SGX_CERT
        )
    if not wallet:
        logger.warning('Both SGX_URL and ETH_PRIVATE_KEY was not provided')
        raise WalletInitializationError('Failed to initialize wallet')
    logger.info(f'Wallet address {wallet.address}')
    return wallet
