from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from .config import (
    BASE_WAITING_TIME,
    GAS_PRICE_INC_PERCENT,
    GRAD_GAS_PRICE_INC_PERCENT,
    MAX_GAS_PRICE,
    MIN_GAS_PRICE_INC
)


@dataclass
class Fee:
    gas_price: Optional[int]
    max_fee: Optional[int]
    priority_fee: Optional[int]


class BaseFeeManager(ABC):
    @abstractmethod
    def next_fee(self, fee: Fee) -> Fee:
        pass

    @abstractmethod
    def inc_fee(self, fee: Fee) -> Fee:
        pass


class FeeManagerV0(BaseFeeManager):
    def inc_gas_price(
        self,
        gas_price: int,
        inc: int = GAS_PRICE_INC_PERCENT
    ) -> int:
        return max(
            gas_price * (100 + inc) // 100,
            gas_price + MIN_GAS_PRICE_INC
        )

    def next_fee(self, fee: Fee) -> Fee:
        ngp = self.inc_gas_price(
            gas_price=fee.gas_price,
            inc=GRAD_GAS_PRICE_INC_PERCENT
        )
        if ngp > self.MAX_GAS_PRICE:
            logger.warning(
                f'Next gas {ngp} price is not allowed. '
                f'Defaulting to {MAX_GAS_PRICE}'
            )
            ngp = MAX_GAS_PRICE
        return max(self.eth.avg_gas_price, ngp)

    def inc_fee(self, fee: Fee) -> Fee:
        pass


class FeeManagerV1(BaseFeeManager):
    pass
