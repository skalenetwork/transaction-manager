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

import logging
import time
from decimal import Decimal
# from json.decoder import JSONDecodeError


# import requests
from skale.wallets import BaseWallet
from skale.utils.web3_utils import get_eth_nonce
from web3 import Web3
from web3.exceptions import TransactionNotFound

from configs import (
    DEFAULT_TIMEOUT,
    GAS_PRICE_INC_PERCENT,
    LONG_TIMEOUT,
    MAX_GAS_PRICE, MAX_GAS_PRICE_COEFF, MAX_RETRY_ITERATIONS
)
from tools.helper import crop_tx_dict


logger = logging.getLogger(__name__)


def get_max_gas_price(web3: Web3) -> int:
    return MAX_GAS_PRICE or MAX_GAS_PRICE_COEFF * web3.eth.gasPrice


def next_gas_price(gas_price: int) -> int:
    return gas_price * (100 + GAS_PRICE_INC_PERCENT) // 100


# def get_receipt2(tx_hash: str) -> dict:
#     data = {'jsonrpc': '2.0', 'method': 'eth_getTransactionReceipt',
#             'params': [tx_hash],
#             'id': 1}
#     response = requests.post(ENDPOINT, json=data)
#     content = response.content
#     try:
#         json_response = response.json()
#     except JSONDecodeError:
#         logger.exception(content)
#     result = json_response.get('result')
#     if result is None:
#         return {}
#     return result


def get_receipt(web3: Web3, tx_hash: str) -> dict:
    try:
        receipt = web3.eth.getTransactionReceipt(tx_hash)
    except TransactionNotFound:
        receipt = {}
    return receipt


def wait_for_receipt(web3: Web3, tx_hash: str,
                     timeout: int = DEFAULT_TIMEOUT,
                     it_timeout: int = 1) -> dict:
    receipt = None
    start_ts = time.time()
    while not receipt and time.time() - start_ts < timeout:
        try:
            receipt = get_receipt(web3, tx_hash)
        except Exception:
            logger.exception('Fetching receipt failed')
        time.sleep(it_timeout)
    return receipt


def sign_and_send(web3: Web3,
                  wallet: BaseWallet,
                  tx_data: dict,
                  max_iter: int = MAX_RETRY_ITERATIONS,
                  timeout: int = DEFAULT_TIMEOUT,
                  long_timeout: int = LONG_TIMEOUT) -> tuple:
    tx_hash, receipt, error = None, None, None
    gas_price = tx_data['gasPrice']
    max_gas_price = get_max_gas_price(web3)
    attempt = 0
    logger.info(f'Sending tx. Wallet: {wallet}, data: {tx_data}')
    while not receipt and attempt < max_iter:
        receipt = None
        sending_req_errored = False
        nonce = get_eth_nonce(web3, wallet.address)
        tx_data.update({'nonce': nonce, 'gasPrice': gas_price})
        cropped_tx = crop_tx_dict(tx_data)

        logger.info(f'Processing tx: {cropped_tx}. Attempt {attempt}')
        if gas_price < max_gas_price:
            try:
                logger.info(f'Sending tx with nonce: {nonce}')
                tx_hash = wallet.sign_and_send(tx_data)
            except ValueError:
                logger.exception('Web3 reported error')
                sending_req_errored = True
        else:
            timeout = long_timeout

        gas_price_gw = Web3.fromWei(Decimal(gas_price), 'gwei')

        logger.info(
            f'Waiting, gas price: {gas_price_gw} Gwei, timeout: {timeout}')
        if tx_hash:
            receipt = wait_for_receipt(web3, tx_hash, timeout=timeout)

        if gas_price < max_gas_price and \
                (receipt == {} or sending_req_errored):
            gas_price = next_gas_price(gas_price)
        attempt += 1

    if tx_hash is None:
        error = 'Transaction was not sent'
    elif receipt == {}:
        error = 'Fetching receipt failed: waiting limit exceded'
    elif receipt is None:
        error = 'Failed to fetch receipt'

    logger.info(f'Done. Hash: {tx_hash}. Attempts: {attempt}. Error: {error}.')
    return tx_hash, error
