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
from contextlib import contextmanager
from typing import Generator, Optional, Tuple

from skale.wallets import BaseWallet  # type: ignore

from .attempt import (
    aquire_attempt,
    Attempt,
    create_next_attempt,
    get_last_attempt,
    grad_inc_gas_price
)
from .config import CONFIRMATION_BLOCKS, UNDERPRICED_RETRIES
from .eth import (
    Eth, is_replacement_underpriced, ReceiptTimeoutError
)
from .transaction import Tx, TxStatus
from .txpool import TxPool

logger = logging.getLogger(__name__)


class ConfirmationError(Exception):
    pass


class SendingError(Exception):
    pass


class WaitTimeoutError(Exception):
    pass


class Processor:
    def __init__(self, eth: Eth, pool: TxPool, wallet: BaseWallet) -> None:
        self.eth: Eth = eth
        self.pool: TxPool = pool
        self.wallet: BaseWallet = wallet
        self.address = wallet.address

    def set_exec_params(
        self,
        tx: Tx,
        gas_price: int,
        nonce: int,
        gas: int
    ) -> None:
        tx.chain_id = self.eth.chain_id
        tx.source = self.wallet.address
        tx.gas_price = gas_price
        tx.nonce = nonce
        tx.gas = gas

    def send(self, tx: Tx) -> None:
        tx_hash, err = None, None
        retry = 0
        while tx_hash is None and retry < UNDERPRICED_RETRIES:
            logger.info('Retry %d', retry)
            logger.info('Signing tx %s ...', tx.tx_id)
            signed = self.wallet.sign(tx.eth_tx)
            logger.info(f'Sending transaction {tx}')
            try:
                tx_hash = self.eth.send_tx(signed)
            except Exception as e:
                logger.info(f'Sending failed with error {err}')
                err = e
                if is_replacement_underpriced(err):
                    logger.info('Replacement gas price is too low. Increasing')
                    tx.gas_price = grad_inc_gas_price(tx.gas_price)
                    retry += 1
                else:
                    break

        if tx_hash is None:
            tx.status = TxStatus.UNSENT
            raise SendingError(err)

        tx.set_as_sent(tx_hash)
        logger.info(f'Tx {tx.tx_id} was sent successfully')

    def wait(self, tx: Tx, attempt: Attempt) -> Optional[int]:
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
        except ReceiptTimeoutError as err:
            logger.info(f'{tx.tx_id} is not mined within {max_time}')
            tx.status = TxStatus.TIMEOUT
            raise WaitTimeoutError(err)

        return self.eth.wait_for_receipt(
            tx_hash=tx.tx_hash,
            max_time=max_time
        )

    def create_attempt(self, tx_id: str, nonce: int, avg_gp: int) -> Attempt:
        prev = get_last_attempt()
        logger.info(f'Previous attempt: {prev}')
        return create_next_attempt(nonce, avg_gp, tx_id, prev)

    def confirm(self, tx: Tx) -> None:
        self.eth.wait_for_blocks(amount=CONFIRMATION_BLOCKS)
        h, r = self.get_exec_data(tx)
        if h is None or r not in (0, 1):
            tx.status = TxStatus.UNCONFIRMED
            raise ConfirmationError('Tx is not confirmed')
        tx.set_as_completed(h, r)
        logger.info('Tx was confirmed %s', tx.tx_id)

    def get_exec_data(self, tx: Tx) -> Tuple[Optional[str], Optional[int]]:
        for h in reversed(tx.hashes):
            r = self.eth.get_status(h)
            if r >= 0:
                return h, r
        return None, None

    def handle(self, tx: Tx) -> None:
        avg_gp = self.eth.avg_gas_price
        logger.info(f'Received avg gas price - {avg_gp}')
        nonce = self.eth.get_nonce(self.address)
        logger.info(f'Received current nonce - {nonce}')

        if tx.is_sent():
            tx_hash, rstatus = self.get_exec_data(tx)
            if rstatus is not None:
                self.confirm(tx)

        attempt = self.create_attempt(tx.tx_id, nonce, avg_gp)
        logger.info(f'Current attempt: {attempt}')

        logger.info(f'Calculating gas for {tx} ...')
        gas = self.eth.calculate_gas(tx.eth_tx, tx.multiplier)

        logger.info(f'Gas for {tx.tx_id}: {tx.gas}')
        with aquire_attempt(attempt, tx) as attempt:
            self.set_exec_params(tx, attempt.gas_price, attempt.nonce, gas)
            self.send(tx, attempt.nonce, attempt.gas_price)
        logger.info(f'Saving tx: {tx.tx_id} record after sending ...')
        self.pool.save(tx)
        logger.info(
            f'Waiting for tx: {tx.tx_id} with hash: {tx.tx_hash} ...'
        )
        rstatus = self.wait(tx, attempt)
        if rstatus is not None:
            self.confirm(tx)

    @contextmanager
    def aquire_tx(self, tx: Tx) -> Generator[Tx, None, None]:
        logger.info('Aquiring %s ...', tx.tx_id)
        tx.attempts += 1
        try:
            yield tx
        finally:
            if tx.is_last_attempt():
                tx.status = TxStatus.DROPPED
            if tx.is_completed():
                self.pool.release(tx)
            else:
                self.pool.save(tx)

    def process_next(self):
        tx = self.pool.fetch_next()
        if tx is not None:
            with self.aquire_tx(tx) as tx:
                self.handle(tx)

    def run(self) -> None:
        while True:
            try:
                self.process_next()
            except Exception:
                logger.exception('Failed to receive next tx')
                logger.info('Waiting for next tx ...')
            finally:
                time.sleep(1)
