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
            logger.info(f'({i}) Signing tx {tx.tx_id} ...')
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
        tx.attempts += 1

    def wait(self, tx: Tx, attempt: Attempt):
        if not tx.tx_hash:
            logger.warning(f'Tx {tx.tx_id} has not any receipt')
            return None
        max_time = attempt.wait_time
        try:
            logger.info(f'Wating for {tx.tx_id}, timeout {max_time} ...')
            self.eth.wait_for_receipt(
                tx_hash=tx.tx_hash,
                max_time=max_time
            )
        except ReceiptTimeoutError:
            logger.info(f'{tx.tx_id} is not mined within {max_time}')
            # TODO: use tx attempt count
            if attempt.is_last():
                tx.status = TxStatus.DROPPED
            else:
                tx.status = TxStatus.TIMEOUT
            return
        tx.status = TxStatus.MINED
        # TODO: Rewrite confirmation
        rstatus = self.eth.wait_for_receipt(
            tx_hash=tx.tx_hash,
            max_time=max_time
        )
        tx.set_as_completed(rstatus)

    def handle(self, tx: Tx) -> None:
        # TODO: use tx.sent and fix mypy issues
        if tx.tx_hash is not None and (r := self.eth.get_status(tx.tx_hash)):
            logger.info(f'Tx {tx.tx_id} is already mined: {tx.tx_hash}')
            tx.set_as_completed(r)
            return

        logger.info(f'Configuring dynamic params for {tx.tx_id} ...')
        avg_gp = self.eth.avg_gas_price
        logger.info(f'Received avg gas pirce - {avg_gp}')
        nonce = self.eth.get_nonce(self.address)
        logger.info(f'Received current nonce - {nonce}')
        prev_attempt = get_last_attempt()
        logger.info(f'Previous attempt: {prev_attempt}')
        attempt = create_next_attempt(
            nonce,
            avg_gp,
            tx.tx_id,
            prev_attempt
        )
        logger.info(f'Current attempt: {attempt}')
        with aquire_attempt(attempt, tx) as attempt:
            self.send(tx, attempt.nonce, attempt.gas_price)
        logger.info(f'Saving tx: {tx.tx_id} record after sending ...')
        self.pool.save(tx)
        logger.info(f'Waiting for tx: {tx.tx_id} with hash: {tx.tx_hash} ...')
        self.wait(tx, attempt)

    def run(self) -> None:
        while True:
            try:
                if self.pool.size > 0:
                    with self.pool.aquire_next() as tx:
                        logger.info(f'Received transaction {tx}')
                        self.handle(tx)
            except Exception:
                logger.exception('Failed to process tx')
            time.sleep(1)
