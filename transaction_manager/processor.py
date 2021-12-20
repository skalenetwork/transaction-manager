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
    acquire_attempt,
    Attempt,
    BaseAttemptManager,
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
    def __init__(
        self,
        eth: Eth,
        pool: TxPool,
        attempt_manager: BaseAttemptManager,
        wallet: BaseWallet
    ) -> None:
        self.eth: Eth = eth
        self.attempt_manager = attempt_manager
        self.pool: TxPool = pool
        self.wallet: BaseWallet = wallet
        self.address = wallet.address

    def send(self, tx: Tx) -> None:
        tx_hash, err = None, None
        retry = 0
        while tx_hash is None and retry < UNDERPRICED_RETRIES:
            logger.info('Retry %d', retry)
            logger.info('Signing tx %s', tx.tx_id)
            etx = self.eth.convert_tx(tx)
            logger.info('IVD %s', etx)
            signed = self.wallet.sign(etx)
            logger.info('Sending transaction %s', tx)
            try:
                tx_hash = self.eth.send_tx(signed)
            except Exception as e:
                logger.info(f'Sending failed with error {err}')
                err = e
                if is_replacement_underpriced(err):
                    logger.info('Replacement gas price is too low. Increasing')
                    gp = tx.fee.gas_price
                    tx.fee.gas_price = grad_inc_gas_price(gp)  # type: ignore
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
            logger.info(f'Waiting for {tx.tx_id}, timeout {max_time}')
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

    def confirm(self, tx: Tx) -> None:
        logger.info(
            'Tx %s: confirming within %d blocks',
            tx.tx_id, CONFIRMATION_BLOCKS
        )
        self.eth.wait_for_blocks(amount=CONFIRMATION_BLOCKS)
        h, r = self.get_exec_data(tx)
        if h is None or r not in (0, 1):
            tx.status = TxStatus.UNCONFIRMED
            raise ConfirmationError('Tx is not confirmed')
        tx.set_as_completed(h, r)
        logger.info('Tx %s was confirmed', tx.tx_id)

    def get_exec_data(self, tx: Tx) -> Tuple[Optional[str], Optional[int]]:
        for h in reversed(tx.hashes):
            r = self.eth.get_status(h)
            if r >= 0:
                return h, r
        return None, None

    def process(self, tx: Tx, prev_attempt: Optional[Attempt]) -> None:
        tx.chain_id = self.eth.chain_id
        tx.source = self.wallet.address

        nonce = self.eth.get_nonce(self.address)
        logger.info(f'Received current nonce - {nonce}')

        if tx.is_sent():
            _, rstatus = self.get_exec_data(tx)
            if rstatus is not None:
                self.confirm(tx)
                return

        attempt = self.attempt_manager.create_next(
            tx.tx_id,
            nonce,
            prev_attempt
        )
        logger.info(f'Current attempt: {attempt}')

        tx.fee, tx.nonce = attempt.fee, attempt.nonce

        logger.info(f'Calculating gas for {tx}')
        tx.gas = self.eth.calculate_gas(tx)
        logger.info(f'Gas for {tx.tx_id}: {tx.gas}')

        with acquire_attempt(attempt, tx) as attempt:
            self.send(tx)

        logger.info(f'Saving tx: {tx.tx_id} record after sending')
        self.pool.save(tx)
        logger.info(f'Waiting for tx: {tx.tx_id} with hash: {tx.tx_hash}')

        rstatus = self.wait(tx, attempt)
        if rstatus is not None:
            self.confirm(tx)

    @contextmanager
    def acquire_tx(self, tx: Tx) -> Generator[Tx, None, None]:
        logger.info('Aquiring %s. Attempt %s', tx.tx_id, tx.attempts)
        tx.attempts += 1
        if tx.status == TxStatus.PROPOSED:
            tx.status = TxStatus.SEEN
        try:
            yield tx
        finally:
            if not tx.is_completed() and tx.is_last_attempt():
                tx.status = TxStatus.DROPPED
            if tx.is_completed():
                self.pool.release(tx)
            else:
                self.pool.save(tx)

    def process_next(self) -> None:
        txs = self.pool.to_list()
        if txs:
            logger.info('Pool: %s', txs)
        tx = self.pool.fetch_next()
        if tx is not None:
            with self.acquire_tx(tx) as tx:
                prev_attempt = get_last_attempt()
                logger.info('Previous attempt %s', prev_attempt)
                self.process(tx, prev_attempt)

    def run(self) -> None:
        while True:
            try:
                self.process_next()
            except Exception:
                logger.exception('Failed to process tx')
                logger.info('Waiting for next tx')
            finally:
                time.sleep(1)
