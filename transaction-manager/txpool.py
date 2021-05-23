""" Process transaction messages from queue """

from contextlib import contextmanager

import redis

from .structures import Tx
from .resources import rs as grs


class TxPool:
    def __init__(
        self, name: str = 'transactions',
        rs: redis.Redis = grs
    ) -> None:
        self.rs: redis.Redis = rs
        self.name: str = name

    def get(self, tx_id: bytes) -> Tx:
        return Tx.from_bytes(self.rs.get(tx_id))

    def get_next(self) -> Tx:
        tx_id = self.rs.zrange(self.name, -1, -1)[0]
        return self.get(tx_id)

    def mark_last(self, tx_id: bytes) -> None:
        self.rs.set('last_tx', tx_id)

    def get_last(self) -> Tx:
        tx_id = self.rs.get('last_tx')
        return self.get(tx_id)

    @contextmanager
    def aquire_next(self) -> Tx:
        tx = self.get_next()
        try:
            yield tx
        finally:
            self.release(tx)

    def release(self, tx: Tx) -> None:
        pipe = self.rs.pipeline()
        if tx.is_completed():
            pipe.zrem(self.name, tx.tx_id)
        pipe.set(tx.tx_id, tx.to_bytes())
        pipe.execute()
