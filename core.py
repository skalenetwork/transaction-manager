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

logger = logging.getLogger(__name__)


def sign_and_send(web3, nonce_manager, transaction_hash, wallet):
    # todo: handle errors and return errors as a dict
    nonce = nonce_manager.transaction_nonce()
    transaction_hash['nonce'] = nonce
    signed_txn = web3.eth.account.sign_transaction(
        transaction_hash,
        private_key=wallet['private_key']
    )
    logger.info(f'Sending transaction with nonce {nonce}...')
    tx = web3.eth.sendRawTransaction(signed_txn.rawTransaction)
    # todo: decrease nonce if cannot send transaction
    logger.info(f'Sent: {transaction_hash} - tx: {tx}')
    return tx
