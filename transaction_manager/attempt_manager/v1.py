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
from ..eth import Eth
from ..structures import Attempt, Fee, Tx
from ..config import (
    BASE_WAITING_TIME,
    GAS_PRICE_INC_PERCENT,
    GRAD_GAS_PRICE_INC_PERCENT,
    MAX_GAS_PRICE,
    MIN_GAS_PRICE_INC_PERCENT
)

logger = logging.getLogger(__name__)


class AttemptManagerV1(BaseAttemptManager):
    def __init__(
        self,
        eth: Eth,
        storage: BaseAttemptStorage,
        source: str,
        current: Optional[Attempt] = None,
        max_gas_price: int = MAX_GAS_PRICE,
        base_waiting_time: int = BASE_WAITING_TIME,
        min_gas_price_inc: int = MIN_GAS_PRICE_INC_PERCENT,
        gas_price_inc_percent: int = GAS_PRICE_INC_PERCENT,
        grad_gas_price_inc_percent: int = GRAD_GAS_PRICE_INC_PERCENT
    ) -> None:
        self.eth = eth
        self.storage = storage
        self.source = source
        self._current = current
        self.max_gas_price = max_gas_price
        self.base_waiting_time = base_waiting_time
        self.min_gas_price_inc = min_gas_price_inc
        self.gas_price_inc_percent = gas_price_inc_percent
        self.grad_gas_price_inc_percent = grad_gas_price_inc_percent

    def fetch(self) -> None:
        self._current = self.storage.get()

    @property
    def current(self) -> Optional[Attempt]:
        return self._current

    @made
    def save(self) -> None:
        self.storage.save(self.current)  # type: ignore

    def next_waiting_time(self, attempt_index: int) -> int:
        return self.base_waiting_time + 10 * (attempt_index ** 2)

    def inc_gas_price(
        self,
        gas_price,
        inc: Optional[int] = None
    ) -> int:
        inc = inc or self.gas_price_inc_percent
        return max(
            gas_price * (100 + inc) // 100,
            gas_price + self.min_gas_price_inc
        )

    @made
    def replace(self, tx, replace_attempt: int = 0) -> None:
        ngp = self.inc_gas_price(
            self.current.fee.gas_price,  # type: ignore
            inc=self.grad_gas_price_inc_percent)
        if ngp > self.max_gas_price:
            logger.warning(
                f'Next gas {ngp} price is not allowed. '
                f'Defaulting to {MAX_GAS_PRICE}'
            )
            ngp = self.max_gas_price
        fee = Fee(gas_price=ngp)  # type: ignore
        tx.fee = self._current.fee = fee  # type: ignore

    def next_gas_price(
        self,
        last_gas_price: int,
        average_gas_price: int
    ) -> int:
        next_gas_price = self.inc_gas_price(last_gas_price)
        if next_gas_price > self.max_gas_price:
            logger.warning(
                f'Next gas {next_gas_price} price is not allowed. '
                f'Defaulting to {MAX_GAS_PRICE}'
            )
            next_gas_price = self.max_gas_price
        return max(average_gas_price, next_gas_price)

    def make(self, tx: Tx) -> None:
        last = self.current

        nonce = self.eth.get_nonce(self.source)
        logger.info(f'Received current nonce - {nonce}')
        avg_gas_price = self.eth.avg_gas_price
        logger.info(f'Received average gas price {avg_gas_price}')

        if last is None or last.fee.gas_price is None or nonce > last.nonce:
            next_gp = avg_gas_price
            next_wait_time = self.base_waiting_time
            next_index = 1
        else:
            next_gp = self.next_gas_price(last.fee.gas_price, avg_gas_price)
            next_index = last.index + 1
            next_wait_time = self.next_waiting_time(next_index)

        logger.info(f'Calculated new gas price {next_gp}')
        fee = Fee(gas_price=next_gp)
        tx.nonce = nonce
        gas = self.eth.calculate_gas(tx)
        logger.info(f'Estimated gas {gas}')
        tx.gas = gas
        tx.fee = fee

        self._current = Attempt(
            tx_id=tx.tx_id,
            nonce=nonce,
            index=next_index,
            fee=fee,
            wait_time=next_wait_time,
            gas=gas
        )
