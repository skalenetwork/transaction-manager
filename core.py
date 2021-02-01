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
from tools.helper import crop_tx_dict

logger = logging.getLogger(__name__)

ATTEMPTS = 3
TIMEOUT = 1

SGX_UNREACHABLE_MESSAGE = 'Sgx server is unreachable'


def sign_and_send(transaction_dict: str, wallet, nonce_manager) -> tuple:
    error, tx = None, None
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
