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

import os
import logging
import json
from http import HTTPStatus
from flask import Response
from time import sleep

from skale.wallets import Web3Wallet, SgxWallet
from configs import (LOCAL_WALLET_FILEPATH, NODE_CONFIG_FILEPATH, LOCAL_WALLET_RETRIES,
                     LOCAL_WALLET_TIMEOUT, SGX_KEY_NAME_RETRIES, SGX_KEY_NAME_TIMEOUT,
                     SGX_CERTIFICATES_FOLDER)


logger = logging.getLogger(__name__)


def construct_response(status, data):
    return Response(
        response=json.dumps(data),
        status=status,
        mimetype='application/json'
    )


def construct_err_response(status, err):
    return construct_response(status, {'data': None, 'error': str(err)})


def construct_ok_response(data=None):
    return construct_response(HTTPStatus.OK, {'data': data, 'error': None})


def retry(exceptions, times, delay=0):
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


def init_wallet(web3):
    """
    Inits SGXWallet if SGX_SERVER_URL found it the env, Web3Wallet otherwise.

    :param Web3 web3: web3 object connected to some network

    :returns Web3Wallet/SGXWallet: Inited Web3Wallet or SGXWallet object
    """
    if os.environ.get('SGX_SERVER_URL'):
        return init_sgx_wallet(web3)
    logger.warning('SGX_SERVER_URL is not provided, going to use software wallet')
    return init_local_wallet(web3)


def init_local_wallet(web3):
    """
    Inits Web3Wallet object with private key name from local wallet.

    :param Web3 web3: web3 object connected to some network

    :returns Web3Wallet: Inited Web3Wallet object
    """
    private_key = get_local_wallet_private_key()
    return Web3Wallet(private_key, web3)


@retry((KeyError, FileNotFoundError), LOCAL_WALLET_RETRIES, LOCAL_WALLET_TIMEOUT)
def get_local_wallet_private_key():
    """
    Reads ETH private key from the local wallet file.
    Retries multiple times if local wallet file or private_key field is not found.
    """
    with open(LOCAL_WALLET_FILEPATH, encoding='utf-8') as data_file:
        wallet_data = json.loads(data_file.read())
    return wallet_data['private_key']


def init_sgx_wallet(web3):
    """
    Inits SgxWallet object with SGX key name from node config
    and SGX server URL from environment.

    :param Web3 web3: web3 object connected to some network

    :returns SgxWallet: Inited SGXWallet object
    """
    sgx_key_name = get_sgx_key_name()
    return SgxWallet(os.environ['SGX_SERVER_URL'],
                     web3,
                     key_name=sgx_key_name,
                     path_to_cert=SGX_CERTIFICATES_FOLDER)


@retry((KeyError, FileNotFoundError), SGX_KEY_NAME_RETRIES, SGX_KEY_NAME_TIMEOUT)
def get_sgx_key_name():
    """
    Reads SGX key name from the node config file.
    Retries multiple times if node config file or sgx_key_name field is not found.
    """
    with open(NODE_CONFIG_FILEPATH, encoding='utf-8') as data_file:
        config = json.loads(data_file.read())
    return config['sgx_key_name']
