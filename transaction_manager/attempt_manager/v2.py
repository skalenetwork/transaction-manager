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
from typing import Optional

from .base import BaseAttemptManager, made
from .storage import BaseAttemptStorage

from ..config import (
    BASE_FEE_INC_PERCENT,
    BASE_WAITING_TIME,
    CAP_TIP_RATIO,
    FEE_INC_PERCENT,
    MAX_FEE_VALUE,
    MAX_TX_CAP,
    MIN_FEE_INC_PERCENT,
    MIN_PRIORITY_FEE
)
from ..eth import Eth
from ..structures import Attempt, Fee, Tx

logger = logging.getLogger(__name__)


class AttemptManagerV2(BaseAttemptManager):
    def __init__(
        self,
        eth: Eth,
        storage: BaseAttemptStorage,
        source: str,
        current: Optional[Attempt] = None,
        base_waiting_time: int = BASE_WAITING_TIME,
        min_priority_fee: int = MIN_PRIORITY_FEE,
        inc_percent: int = FEE_INC_PERCENT,
        min_inc_percent: int = MIN_FEE_INC_PERCENT,
        max_fee: int = MAX_FEE_VALUE,
        cap_tip_ratio: int = CAP_TIP_RATIO,
        max_tx_cap: int = MAX_TX_CAP,
        base_fee_inc_percent: int = BASE_FEE_INC_PERCENT
    ) -> None:
        self.eth = eth
        self._current = current
        self.storage = storage
        self.source = source
        self.base_waiting_time = base_waiting_time
        self.min_priority_fee = min_priority_fee
        self.inc_percent = inc_percent
        self.min_inc_percent = min_inc_percent
        self.max_fee = max_fee
        self.base_fee_inc_percent = base_fee_inc_percent

    def fetch(self) -> None:
        self._current = self.storage.get()

    @property
    def current(self) -> Optional[Attempt]:
        return self._current

    @made
    def save(self) -> None:
        self.storage.save(self.current)  # type: ignore

    def inc_fee_value(self, fee_value: int, inc: Optional[int] = None) -> int:
        inc = inc or self.inc_percent
        return min(
            max(
                fee_value * (100 + inc) // 100,
                fee_value + self.min_inc_percent
            ),
            self.max_fee
        )

    @made
    def replace(self, tx: Tx) -> None:
        next_pf = self.inc_fee_value(
            self.current.fee.max_priority_fee_per_gas,  # type: ignore
            inc=self.min_inc_percent
        )
        next_mf = self.inc_fee_value(
            self.current.fee.max_fee_per_gas,  # type: ignore
            inc=self.min_inc_percent
        )
        if next_mf == self.max_fee:
            logger.warning(
                f'Next priority fee {next_pf} is not allowed. '
                f'Defaulting to {self.max_fee}'
            )
        fee = Fee(max_priority_fee_per_gas=next_pf, max_fee_per_gas=next_mf)
        tx.fee = self._current.fee = fee  # type: ignore

    def next_fee_value(self, fee_value: int) -> int:
        return self.inc_fee_value(fee_value)

    def next_waiting_time(self, attempt_index: int) -> int:
        return self.base_waiting_time + 10 * (attempt_index ** 2)

    def max_allowed_fee(self, gas: int, value: int) -> int:
        balance = self.eth.get_balance(self.source)
        return balance - value // gas

    def calculate_initial_fee(self):
        history = self.eth.fee_history()
        estimated_base_fee = history['baseFeePerGas'][-1]
        tip = max(self.min_priority_fee, history['reward'][0][-1])
        gap = self.base_fee_inc_percent * max(tip, estimated_base_fee)
        return Fee(max_priority_fee_per_gas=tip, max_fee_per_gas=gap)

    def make(self, tx: Tx) -> None:
        last = self.current
        nonce = self.eth.get_nonce(self.source)
        logger.info(f'Received current nonce - {nonce}')
        if last is None or nonce > last.nonce or last.fee is None:
            next_index = 1
            next_fee = self.calculate_initial_fee()
            next_wait_time = self.base_waiting_time
        else:
            next_index = last.index + 1
            next_pf = self.next_fee_value(
                last.fee.max_priority_fee_per_gas  # type: ignore
            )
            next_mf = self.next_fee_value(
                last.fee.max_fee_per_gas  # type: ignore
            )
            next_fee = Fee(
                max_priority_fee_per_gas=next_pf,
                max_fee_per_gas=next_mf
            )
            next_wait_time = self.next_waiting_time(next_index)

        logger.info('Next fee %s', next_fee)
        tx.fee, tx.nonce = next_fee, nonce
        estimated_gas = self.eth.calculate_gas(tx)
        logger.info('Estimated gas %d', estimated_gas)
        if tx.gas:
            allowed_fee = self.max_allowed_fee(tx.gas, tx.value)
            if allowed_fee < next_fee.max_fee_per_gas:
                logger.warning(
                    'Suggested fee exceeds allowance. Defaulting to %d',
                    estimated_gas
                )
                tx.gas = estimated_gas
            else:
                logger.info(
                    'Estimated gas will be ignored in favor of %d',
                    tx.gas
                )
        else:
            tx.gas = estimated_gas

        self._current = Attempt(
            tx_id=tx.tx_id,
            nonce=nonce,
            index=next_index,
            fee=next_fee,
            wait_time=next_wait_time,
            gas=tx.gas
        )
