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

logger = logging.getLogger(__name__)


ATTEMPTS = 3
TIMEOUT = 1


def sign_and_send(transaction_dict, wallet, nonce_manager):
    error = None
    for attempt in range(ATTEMPTS):
        try:
            transaction_dict['nonce'] = nonce_manager.nonce
            logger.info(f'Signing transaction with {nonce_manager.nonce}')
            tx = wallet.sign_and_send(transaction_dict)
        except Exception as e:  # todo: catch specific error
            logger.error('Error occured', exc_info=e)
            nonce_manager.fix_nonce()
            time.sleep(TIMEOUT)
            error = e
        else:
            error = None
            break
    if error is not None:
        raise error
    logger.info('Incrementing nonce...')
    nonce_manager.increment()
    logger.info(f'Transaction sent - tx: {tx}, '
                f'nonce: {transaction_dict["nonce"]}')
    return tx
