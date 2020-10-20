#   -*- coding: utf-8 -*-
#
#   This file is part of SKALE Transaction Manager
#
#   Copyright (C) 2019 SKALE Labs
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

import json
import logging
import os
from time import sleep

from skale.wallets import BaseWallet, SgxWallet, Web3Wallet
from web3 import Web3

from configs import NODE_CONFIG_FILEPATH, SGX_KEY_NAME_RETRIES, SGX_KEY_NAME_TIMEOUT
from configs.sgx import SGX_CERTIFICATES_FOLDER


logger = logging.getLogger(__name__)


class WalletInitError(Exception):
    """Raised when wallet initialization fails"""


def retry(exceptions: list, times: int, delay: int = 0):
    """
    Retry Decorator

    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown

    :param Exceptions: Lists of exceptions that trigger a retry attempt
    :type Exceptions: Tuple of Exceptions
    :param times: The number of times to repeat the wrapped function/method
    :type times: Int
    :param delay: Delay between attempts in seconds. default: 0
    :type delay: Int
    """
    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    logger.info(
                        'Exception thrown when attempting to run %s, attempt '
                        '%d of %d' % (func, attempt, times),
                        exc_info=True
                    )
                    attempt += 1
                    sleep(delay)
            return func(*args, **kwargs)
        return newfn
    return decorator


def init_wallet(web3: Web3) -> BaseWallet:
    """
    Inits SGXWallet if SGX_SERVER_URL found it the env, Web3Wallet otherwise.

    :param Web3 web3: web3 object connected to some network

    :returns Web3Wallet/SGXWallet: Inited Web3Wallet or SGXWallet object
    """

    PK_FILE = os.getenv('PK_FILE')
    SGX_SERVER_URL = os.getenv('SGX_SERVER_URL')
    if SGX_SERVER_URL:
        return init_sgx_wallet(SGX_SERVER_URL, web3)
    if PK_FILE:
        return init_web3_wallet(web3, PK_FILE)

    raise WalletInitError(
        'Unable to initialize wallet - provide PK_FILE or SGX_SERVER_URL env variable')


def init_web3_wallet(web3: Web3, pk_file: str) -> Web3Wallet:
    """
    Inits Web3Wallet object with private key from provided file.

    :param Web3 web3: web3 object connected to some network
    :param str pk_flie: path to the file with private key

    :returns Web3Wallet: Inited Web3Wallet object
    """
    with open(pk_file, 'r') as f:
        pk = str(f.read()).strip()
    return Web3Wallet(pk, web3)


def init_sgx_wallet(sgx_server_url: str, web3: Web3) -> SgxWallet:
    """
    Inits SgxWallet object with SGX key name from node config
    and SGX server URL from environment.

    :param str sgx_server_url: URL of the SGX server
    :param Web3 web3: web3 object connected to some network

    :returns SgxWallet: Inited SGXWallet object
    """
    sgx_key_name = get_sgx_key_name()
    logger.info(
        'Initializing SgxWallet'
        f'Server URL: {sgx_server_url} '
        f'Key name: {sgx_key_name} '
        f'Path to cert: {SGX_CERTIFICATES_FOLDER}'
    )
    return SgxWallet(
        sgx_server_url,
        web3,
        key_name=sgx_key_name,
        path_to_cert=SGX_CERTIFICATES_FOLDER
    )


@retry((KeyError, FileNotFoundError), SGX_KEY_NAME_RETRIES, SGX_KEY_NAME_TIMEOUT)
def get_sgx_key_name() -> str:
    """
    Reads SGX key name from the node config file.
    Retries multiple times if node config file or sgx_key_name field is not found.
    """
    with open(NODE_CONFIG_FILEPATH, encoding='utf-8') as data_file:
        config = json.loads(data_file.read())
    return config['sgx_key_name']
