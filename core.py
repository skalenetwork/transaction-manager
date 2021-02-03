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


from sgx.http import SgxUnreachableError
from web3._utils.transactions import get_block_gas_limit

from tools.helper import crop_tx_dict

logger = logging.getLogger(__name__)

ATTEMPTS = 3
TIMEOUT = 1

SGX_UNREACHABLE_MESSAGE = 'Sgx server is unreachable'
SUCCESS_STATUS = 1
GAS_LIMIT_COEFFICIENT = 1.2


def sign_and_send(transaction_dict: dict, wallet, nonce_manager) -> tuple:
    error, tx = None, None
    dry_run_result, estimated_gas = execute_dry_run(nonce_manager.web3, wallet, transaction_dict)
    if not is_success(dry_run_result):
        error = f'Dry run failed: {dry_run_result["error"]}'
    else:
        for attempt in range(ATTEMPTS):
            try:
                nonce = nonce_manager.nonce
                transaction_dict['nonce'] = nonce
                cropped_tx = crop_tx_dict(transaction_dict)
                logger.info(f'Transaction data {cropped_tx}')
                logger.info(f'Signing transaction with nonce: {nonce}')
                tx = wallet.sign_and_send(transaction_dict)
            except SgxUnreachableError:
                error = SGX_UNREACHABLE_MESSAGE
                break
            except Exception as e:  # todo: catch specific error
                logger.error('Error occured', exc_info=e)
                nonce_manager.fix_nonce()
                time.sleep(TIMEOUT)
                error = str(e)
            else:
                error = None
                break
    if tx is not None and error is None:
        logger.info('Incrementing nonce...')
        nonce_manager.increment()
        logger.info(f'Transaction sent - tx: {tx}, '
                    f'nonce: {transaction_dict["nonce"]}')
    return tx, error


def is_success(result: dict) -> bool:
    return result.get('status') == SUCCESS_STATUS


def execute_dry_run(web3, wallet, transaction_dict: dict) -> tuple:
    dry_run_result = make_dry_run_call(web3, wallet, transaction_dict)
    estimated_gas_limit = None
    if dry_run_result['status'] == SUCCESS_STATUS:
        estimated_gas_limit = dry_run_result['payload']
    return dry_run_result, estimated_gas_limit


def make_dry_run_call(web3, wallet, transaction_dict: dict) -> dict:
    logger.info(
        f'Dry run tx, '
        f'sender: {wallet.address}, '
        f'wallet: {wallet.__class__.__name__}, '
    )

    try:
        if 'gas' in transaction_dict:
            estimated_gas = transaction_dict['gas']
            web3.eth.call(transaction_dict)
        else:
            estimated_gas = estimate_gas(web3, transaction_dict)
            logger.info(f'Estimated gas for tx: {estimated_gas}')
    except Exception as err:
        logger.error('Dry run for tx failed with error', exc_info=err)
        return {'status': 0, 'error': str(err)}

    return {'status': 1, 'payload': estimated_gas}


def estimate_gas(web3, transaction_dict: dict):
    try:
        block_gas_limit = get_block_gas_limit(web3)
    except AttributeError:
        block_gas_limit = get_block_gas_limit(web3)

    estimated_gas = web3.eth.estimateGas(transaction_dict)
    normalized_estimated_gas = int(estimated_gas * GAS_LIMIT_COEFFICIENT)
    if normalized_estimated_gas > block_gas_limit:
        logger.warning('Estimate gas for tx exceeds block gas limit')
        return block_gas_limit
    return normalized_estimated_gas
