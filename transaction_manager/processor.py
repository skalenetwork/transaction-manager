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
import time

from skale.wallets import BaseWallet  # type: ignore

from .attempt import (
    aquire_attempt,
    Attempt,
    create_next_attempt,
    get_last_attempt,
    grad_inc_gas_price
)
from .config import CONFIRMATION_BLOCKS
from .eth import (
    Eth, is_replacement_underpriced, ReceiptTimeoutError
)
from .transaction import Tx, TxStatus
from .txpool import TxPool

logger = logging.getLogger(__name__)

REPLACEMENT_UNDERPRICED_RETRIES = 5


class Processor:
    def __init__(self, eth: Eth, pool: TxPool, wallet: BaseWallet) -> None:
        self.eth: Eth = eth
        self.pool: TxPool = pool
        self.wallet: BaseWallet = wallet
        self.address = wallet.address

    def send(self, tx: Tx, nonce: int, gas_price: int) -> None:
        tx.chain_id = self.eth.chain_id
        tx.source = self.wallet.address
        tx.gas_price = gas_price
        tx.nonce = nonce

        logger.info(f'Calculating gas for {tx} ...')
        tx.gas = self.eth.calculate_gas(tx.eth_tx)
        logger.info(f'Gas for {tx.tx_id}: {tx.gas}')

        for i in range(REPLACEMENT_UNDERPRICED_RETRIES):
            logger.info('Retry %d', i)
            logger.info('Signing tx %s ...', tx.tx_id)
            signed = self.wallet.sign(tx.eth_tx)
            try:
                logger.info(f'Sending transaction {tx}')
                tx.tx_hash = self.eth.send_tx(signed)
            except Exception as err:
                logger.info(f'Sending failed with error {err}')
                if is_replacement_underpriced(err):
                    logger.info(
                        'Replacement gas price is too low. Trying to increase'
                    )
                    gas_price = grad_inc_gas_price(gas_price)
                else:
                    raise err
            else:
                break

        logger.info(f'Transaction {tx.tx_id} was sent successfully')
        tx.status = TxStatus.SENT
        tx.sent_ts = int(time.time())

    def wait(self, tx: Tx, attempt: Attempt):
        if not tx.tx_hash:
            logger.warning(f'Tx {tx.tx_id} has not any receipt')
            return None
        max_time = attempt.wait_time
        try:
            logger.info(f'Waiting for {tx.tx_id}, timeout {max_time} ...')
            self.eth.wait_for_receipt(
                tx_hash=tx.tx_hash,
                max_time=max_time
            )
        except ReceiptTimeoutError:
            logger.info(f'{tx.tx_id} is not mined within {max_time}')
            tx.status = TxStatus.TIMEOUT
        tx.status = TxStatus.MINED
        self.eth.wait_for_receipt(
            tx_hash=tx.tx_hash,
            max_time=max_time
        )

    def create_attempt(self, tx_id: str) -> Attempt:
        avg_gp = self.eth.avg_gas_price
        logger.info(f'Received avg gas price - {avg_gp}')
        nonce = self.eth.get_nonce(self.address)
        logger.info(f'Received current nonce - {nonce}')
        prev = get_last_attempt()
        logger.info(f'Previous attempt: {prev}')
        return create_next_attempt(nonce, avg_gp, tx_id, prev)

    def confirm(self, tx: Tx) -> None:
        self.eth.wait_for_blocks(amount=CONFIRMATION_BLOCKS)
        r = self.eth.get_status(tx.tx_hash)
        if r < 0:
            raise Exception()
        tx.set_as_completed(r)

    def handle(self, tx: Tx) -> None:
        if tx.is_sent():
            r = self.eth.get_status(tx.tx_hash)
            logger.info('Tx %s has receipt status %d', tx.tx_id, r)
            if r >= 0 and tx.status != TxStatus.MINED:
                tx.status = TxStatus.MINED

        if tx.is_mined():
            logger.info(f'Configuring attempt params for {tx.tx_id} ...')
            attempt = self.create_attempt(tx.tx_id)
            logger.info(f'Current attempt: {attempt}')
            with aquire_attempt(attempt, tx) as attempt:
                self.send(tx, attempt.nonce, attempt.gas_price)
            logger.info(f'Saving tx: {tx.tx_id} record after sending ...')
            self.pool.save(tx)
            logger.info(f'Waiting for tx: {tx.tx_id} with hash: {tx.tx_hash} ...')
            self.wait(tx, attempt)
        self.confirm(tx)

    def run(self) -> None:
        while True:
            # TODO: count attempts here add drop tx here instead of pool
            # TODO: Make pool only handle redis
            try:
                if self.pool.size > 0:
                    with self.pool.aquire_next() as tx:
                        logger.info(f'Received transaction {tx}')
                        tx.attempt += 1
                        try:
                            self.handle(tx)
                        except Exception:
                            if not tx.is_completed() and tx.is_last_attempt():
                                tx.status = TxStatus.DROPPED
            except Exception:
                logger.exception('Failed to receive next tx')
                logger.info('Waiting for next tx ...')
            time.sleep(1)
