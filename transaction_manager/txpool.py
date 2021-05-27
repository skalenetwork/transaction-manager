""" Process transaction messages from queue """

from contextlib import contextmanager
from typing import Generator, Optional

import redis

from .transaction import Tx
from .resources import rs as grs


class NoNextTransactionError(Exception):
    pass


class TxPool:
    def __init__(
        self, name: str = 'transactions',
        rs: redis.Redis = grs
    ) -> None:
        self.rs: redis.Redis = rs
        self.name: str = name

    @property
    def size(self) -> int:
        return self.rs.zcard(self.name)

    def get(self, tx_id: bytes) -> Optional[Tx]:
        return Tx.from_bytes(tx_id, self.rs.get(tx_id))

    def get_next(self) -> Optional[Tx]:
        if self.size == 0:
            return None
        tx_id = self.rs.zrange(self.name, -1, -1)[0]
        return self.get(tx_id)

    def set_last_id(self, tx_id: bytes) -> None:
        self.rs.set('last_id', tx_id)

    def get_last_id(self) -> bytes:
        return self.rs.get('last_id')

    def get_last(self) -> Optional[Tx]:
        tx_id = self.get_last_id()
        if tx_id is None:
            return None
        return self.get(tx_id)

    def clear(self) -> None:
        for tx_id, _ in self.rs.zscan_iter(self.name):
            self.drop(tx_id)

    def drop(self, tx_id: bytes) -> None:
        pipe = self.rs.pipeline()
        pipe.zrem(self.name, tx_id)
        pipe.delete(tx_id)
        pipe.execute()

    @contextmanager
    def aquire_next(self) -> Generator[Tx, None, None]:
        tx = self.get_next()
        # TODO: IVD Revise
        if tx is None:
            raise NoNextTransactionError(f'No transactions in {self.name}')
        self.set_last_id(tx.raw_id)
        try:
            yield tx
        finally:
            self.release(tx)

    def release(self, tx: Tx) -> None:
        pipe = self.rs.pipeline()
        if tx.is_sent():
            pipe.set(tx.tx_id, tx.to_bytes())
        if tx.is_completed():
            pipe.zrem(self.name, tx.tx_id)
        pipe.execute()
