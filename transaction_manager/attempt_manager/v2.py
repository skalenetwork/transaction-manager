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
    BASE_PRIORITY_FEE,
    BASE_WAITING_TIME,
    FEE_INC_PERCENT,
    MAX_FEE_VALUE,
    MAX_PRIORITY_FEE_VALUE,
    MIN_FEE_INC_PERCENT
)
from ..eth import Eth
from ..structures import Attempt, Fee, Tx

logger = logging.getLogger(__name__)


class AttemptManagerV2(BaseAttemptManager):
    def __init__(
        self,
        eth: Eth,
        storage: BaseAttemptStorage,
        current: Optional[Attempt] = None,
        base_waiting_time: int = BASE_WAITING_TIME,
        base_priority_fee: int = BASE_PRIORITY_FEE,
        inc_percent: int = FEE_INC_PERCENT,
        min_inc_percent: int = MIN_FEE_INC_PERCENT,
        max_priority_fee: int = MAX_PRIORITY_FEE_VALUE,
        max_fee: int = MAX_FEE_VALUE,
    ) -> None:
        self.eth = eth
        self._current = current
        self.storage = storage
        self.base_waiting_time = base_waiting_time
        self.base_priority_fee = base_priority_fee
        self.inc_percent = inc_percent
        self.min_inc_percent = min_inc_percent
        self.max_fee = max_fee
        self.max_priority_fee = max_priority_fee

    def fetch(self) -> None:
        self._current = self.storage.get()

    @property
    def current(self) -> Optional[Attempt]:
        return self._current

    @made
    def save(self) -> None:
        self.storage.save(self.current)  # type: ignore

    def inc_priority_fee(
        self,
        fee_value: int,
        inc: Optional[int] = None
    ) -> int:
        inc = inc or self.inc_percent
        return min(
            max(
                fee_value * (100 + inc) // 100,
                fee_value + self.min_inc_percent
            ),
            self.max_priority_fee
        )

    @made
    def replace(self, tx: Tx) -> None:
        next_pf = self.inc_priority_fee(
            self.current.fee.max_priority_fee_per_gas,  # type: ignore
            inc=self.min_inc_percent
        )
        if next_pf == self.max_priority_fee:
            logger.warning(
                f'Next priority fee {next_pf} is not allowed. '
                f'Defaulting to {self.max_fee}'
            )
        fee = Fee(
            max_priority_fee_per_gas=next_pf,
            max_fee_per_gas=self.max_fee
        )
        tx.fee = self._current.fee = fee  # type: ignore

    def next_fee(self, fee: Fee) -> Fee:
        priority_fee_value = fee.max_priority_fee_per_gas or \
            self.base_priority_fee
        next_priority_fee_value = self.inc_priority_fee(priority_fee_value)
        return Fee(
            max_fee_per_gas=fee.max_fee_per_gas,
            max_priority_fee_per_gas=next_priority_fee_value
        )

    def next_waiting_time(self, attempt_index: int) -> int:
        return self.base_waiting_time + 10 * (attempt_index ** 2)

    def make(self, tx: Tx) -> None:
        last = self.current
        nonce = tx.nonce or 0
        if last is None or nonce > last.nonce or last.fee is None:
            next_index = 1
            next_fee = Fee(
                max_fee_per_gas=self.max_fee,
                max_priority_fee_per_gas=self.base_priority_fee
            )
            next_wait_time = self.base_waiting_time
        else:
            next_index = last.index + 1
            next_fee = self.next_fee(last.fee)
            next_wait_time = self.next_waiting_time(next_index)

        logger.info(f'Calculated new fee {next_fee}')
        tx.fee = next_fee
        gas = self.eth.calculate_gas(tx)
        logger.info(f'Estimated gas {gas}')
        tx.gas = gas

        self._current = Attempt(
            tx_id=tx.tx_id,
            nonce=nonce,
            index=next_index,
            fee=next_fee,
            wait_time=next_wait_time,
            gas=gas
        )
