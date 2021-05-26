import json
import logging
from dataclasses import asdict, dataclass
from typing import Optional

import redis

from .resources import rs as grs

logger = logging.getLogger(__name__)

# TODO: IVD Move to options
MAX_RESUBMIT_TIME = 10
GAS_PRICE_INC_PERCENT = 10
MAX_GAS_PRICE = 3 * 10 ** 9
BASE_WAITING_TIME = 10


class GasPriceLimitExceededError(Exception):
    pass


@dataclass
class Attempt:
    tx_id: str
    nonce: int
    index: int
    gas_price: int
    wait_time: int

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self)).encode('utf-8')

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
    # TODO: IVD Better formula needed
    return BASE_WAITING_TIME + 15 * attempt_index


def calculate_next_gas_price(
    last_attempt: Attempt,
    avg_gp: int,
    nonce: int
) -> int:
    inc_gp = last_attempt.gas_price * (100 + GAS_PRICE_INC_PERCENT) // 100
    if inc_gp > MAX_GAS_PRICE:
        logger.warning(
            f'Next gas price is not allowed ({inc_gp} > {MAX_GAS_PRICE})'
        )
        raise GasPriceLimitExceededError(
            f'Next gas price {inc_gp} is not allowed'
        )
    return max(avg_gp, inc_gp)


def make_next_attempt(
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
