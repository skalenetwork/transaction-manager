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

import json
import logging
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Generator, Optional

import redis

from .eth import Eth
from .resources import rs as grs
from .transaction import Fee, Tx, TxStatus
from .config import (
    BASE_WAITING_TIME,
    GAS_PRICE_INC_PERCENT,
    GRAD_GAS_PRICE_INC_PERCENT,
    MAX_GAS_PRICE,
    MIN_GAS_PRICE_INC
)

logger = logging.getLogger(__name__)


@dataclass
class Attempt:
    tx_id: str
    nonce: int
    index: int
    fee: Fee
    wait_time: int

    def __post_init__(self):
        if isinstance(self.fee, dict):
            self.fee = Fee(**self.fee)

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self), sort_keys=True).encode('utf-8')

    @classmethod
    def from_bytes(cls, attempt_bytes: bytes) -> 'Attempt':
        raw = json.loads(attempt_bytes.decode('utf-8'))
        if gas_price := raw.get('gas_price') or None:
            raw.update({'fee': asdict(Fee(gas_price=gas_price))})
            del raw['gas_price']
        return Attempt(**raw)


def get_last_attempt(rs: redis.Redis = grs) -> Optional[Attempt]:
    attempt_bytes = rs.get(b'last_attempt')
    if not attempt_bytes:
        return None
    return Attempt.from_bytes(attempt_bytes)


def set_last_attempt(attempt: Attempt, rs: redis.Redis = grs) -> None:
    rs.set(b'last_attempt', attempt.to_bytes())


def calculate_next_waiting_time(attempt_index: int) -> int:
    return BASE_WAITING_TIME + 10 * (attempt_index ** 2)


def inc_gas_price(gas_price: int, inc: int = GAS_PRICE_INC_PERCENT) -> int:
    return max(gas_price * (100 + inc) // 100, gas_price + MIN_GAS_PRICE_INC)


def grad_inc_gas_price(gas_price: int) -> int:
    ngp = inc_gas_price(gas_price=gas_price, inc=GRAD_GAS_PRICE_INC_PERCENT)
    if ngp < MAX_GAS_PRICE:
        logger.warning(
            f'Next gas {ngp} price is not allowed. '
            f'Defaulting to {MAX_GAS_PRICE}'
        )
        return ngp
    else:
        return MAX_GAS_PRICE


class BaseAttemptManager(metaclass=ABCMeta):
    @abstractmethod
    def create_next(
        self,
        tx_id: str,
        nonce: int,
        last: Optional[Attempt]
    ) -> Attempt:
        pass


class AttemptManagerV1(BaseAttemptManager):
    def __init__(
        self,
        eth: Eth,
        max_gas_price: int = MAX_GAS_PRICE,
        base_waiting_time: int = BASE_WAITING_TIME,
        min_gas_price_inc: int = MIN_GAS_PRICE_INC,
        gas_price_inc_percent: int = GAS_PRICE_INC_PERCENT,
        grad_gas_price_inc_percent: int = GRAD_GAS_PRICE_INC_PERCENT
    ) -> None:
        self.eth = eth
        self.max_gas_price = max_gas_price
        self.base_waiting_time = base_waiting_time
        self.min_gas_price_inc = min_gas_price_inc
        self.gas_price_inc_percent = gas_price_inc_percent
        self.grad_gas_price_inc_percent = GRAD_GAS_PRICE_INC_PERCENT

    def next_waiting_time(self, attempt_index: int) -> int:
        return self.base_waiting_time + 10 * (attempt_index ** 2)

    @classmethod
    def inc_gas_price(
        self,
        gas_price: int,
        inc: Optional[int] = None
    ) -> int:
        inc = inc or self.gas_price_inc_percent
        return max(
            gas_price * (100 + inc) // 100,
            gas_price + self.min_gas_price_inc
        )

    def grad_inc_gas_price(self, gas_price: int) -> int:
        ngp = self.inc_gas_price(
            gas_price=gas_price,
            inc=self.grad_gas_price_inc_percent)
        if ngp < self.max_gas_price:
            logger.warning(
                f'Next gas {ngp} price is not allowed. '
                f'Defaulting to {MAX_GAS_PRICE}'
            )
            return ngp
        else:
            return self.max_gas_price

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
            ngp = self.max_gas_price
        return max(average_gas_price, ngp)

    def create_next(
        self,
        tx_id: str,
        nonce: int,
        last: Optional[Attempt]
    ) -> Attempt:
        avg_gas_price = self.eth.avg_gas_price
        if last is None or last.fee.gas_price is None or nonce > last.nonce:
            next_gp = avg_gas_price
            next_wait_time = self.base_waiting_time
            next_index = 1
        else:
            next_gp = self.next_gas_price(last.fee.gas_price, avg_gas_price)
            next_index = last.index + 1
            next_wait_time = self.next_waiting_time(next_index)
        return Attempt(
            tx_id=tx_id,
            nonce=nonce,
            index=next_index,
            fee=Fee(gas_price=next_gp),
            wait_time=next_wait_time
        )


@contextmanager
def acquire_attempt(
    attempt: Attempt,
    tx: Tx
) -> Generator[Attempt, None, None]:
    logger.info(f'Acquiring attempt {attempt}')
    try:
        yield attempt
    finally:
        if tx.status == TxStatus.SENT:
            set_last_attempt(attempt)
