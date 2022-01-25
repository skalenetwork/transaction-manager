#   -*- coding: utf-8 -*-
#
#   This file is part of SKALE Transaction Manager
#
#   Copyright (C) 2021 SKALE Labs
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
from typing import Optional

from skale.wallets import BaseWallet, SgxWallet, Web3Wallet  # type: ignore
from web3 import Web3

from .config import ETH_PRIVATE_KEY, NODE_DATA_PATH, SGX_URL
from .node import wait_for_sgx_keyname
from .resources import w3 as gw3

logger = logging.getLogger(__name__)

PATH_TO_SGX_CERT = os.path.join(NODE_DATA_PATH, 'sgx_certs')


class WalletInitializationError(Exception):
    pass


def init_wallet(
    w3: Web3 = gw3,
    config_filepath: Optional[str] = None,
    path_to_cert: Optional[str] = None
) -> BaseWallet:
    wallet = None
    if SGX_URL:
        path_to_cert = path_to_cert or PATH_TO_SGX_CERT
        logger.info(f'Initializing sgx wallet {SGX_URL}')
        keyname = wait_for_sgx_keyname(config_filepath=config_filepath)
        wallet = SgxWallet(
            SGX_URL,
            w3,
            key_name=keyname,
            path_to_cert=path_to_cert
        )
    elif ETH_PRIVATE_KEY:
        logger.info('Initializing web3 wallet')
        wallet = Web3Wallet(ETH_PRIVATE_KEY, w3)
    if not wallet:
        logger.warning('Both SGX_URL and ETH_PRIVATE_KEY was not provided')
        raise WalletInitializationError('Failed to initialize wallet')
    logger.info(f'Wallet address {wallet.address}')
    return wallet
