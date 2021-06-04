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
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import Generator, Optional

import redis

from .resources import rs as grs
from .transaction import Tx, TxStatus
from .config import (
    BASE_WAITING_TIME,
    GAS_PRICE_INC_PERCENT,
    GRAD_GAS_PRICE_INC_PERCENT,
    MAX_GAS_PRICE
)

logger = logging.getLogger(__name__)


@dataclass
class Attempt:
    tx_id: str
    nonce: int
    index: int
    gas_price: int
    wait_time: int

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self), sort_keys=True).encode('utf-8')

    @classmethod
    def from_bytes(cls, attempt_bytes: bytes) -> 'Attempt':
        raw = json.loads(attempt_bytes.decode('utf-8'))
        return Attempt(**raw)


def get_last_attempt(rs: redis.Redis = grs) -> Optional[Attempt]:
    attempt_bytes = rs.get(b'last_attempt')
    if not attempt_bytes:
        return None
    return Attempt.from_bytes(attempt_bytes)


def set_last_attempt(attempt: Attempt, rs: redis.Redis = grs) -> None:
    rs.set(b'last_attempt', attempt.to_bytes())


def calculate_next_waiting_time(attempt_index: int) -> int:
    # TODO: Better formula needed
    return BASE_WAITING_TIME + 15 * attempt_index


def inc_gas_price(gas_price: int, inc: int = GAS_PRICE_INC_PERCENT) -> int:
    return gas_price * (100 + inc) // 100


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


def calculate_next_gas_price(
    last_attempt: Attempt,
    avg_gp: int,
    nonce: int
) -> int:
    ngp = inc_gas_price(last_attempt.gas_price, inc=GAS_PRICE_INC_PERCENT)
    if ngp > MAX_GAS_PRICE:
        logger.warning(
            f'Next gas {ngp} price is not allowed. '
            f'Defaulting to {MAX_GAS_PRICE}'
        )
        ngp = MAX_GAS_PRICE
    return max(avg_gp, ngp)


def create_next_attempt(
    nonce: int,
    avg_gas_price: int,
    tx_id: str,
    last: Optional[Attempt] = None
) -> Attempt:
    if last is None or nonce > last.nonce:
        next_gp = avg_gas_price
        next_wait_time = BASE_WAITING_TIME
        next_index = 1
    else:
        next_gp = calculate_next_gas_price(last, avg_gas_price, nonce)
        next_wait_time = calculate_next_waiting_time(last.index)
        next_index = last.index + 1
    return Attempt(
        tx_id=tx_id,
        nonce=nonce,
        index=next_index,
        gas_price=next_gp,
        wait_time=next_wait_time
    )


@contextmanager
def acquire_attempt(
    attempt: Attempt,
    tx: Tx
) -> Generator[Attempt, None, None]:
    logger.info(f'Acquiring attempt {attempt} ...')
    try:
        yield attempt
    finally:
        if tx.status == TxStatus.SENT:
            set_last_attempt(attempt)
