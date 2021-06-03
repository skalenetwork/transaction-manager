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

import redis

from .transaction import InvalidFormatError, Tx
from .resources import rs as grs


logger = logging.getLogger(__name__)


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
        if tx_id is None:
            return None
        r = self.rs.get(tx_id)
        tx = None
        try:
            tx = Tx.from_bytes(tx_id, r)
            if tx is None:
                logger.error('Tx %s has no record', tx_id)
        except InvalidFormatError:
            logger.error('Invalid record for %s', tx_id)
            tx = None
        return tx

    def get_next_id(self) -> Optional[bytes]:
        if self.size == 0:
            return None
        return self.rs.zrange(self.name, -1, -1)[0]

    def _add_record(
        self, tx_id: bytes,
        priority: int,
        tx_record: bytes
    ) -> None:
        pipe = self.rs.pipeline()
        pipe.zadd(self.name, {tx_id: priority})
        pipe.set(tx_id, tx_record)
        pipe.execute()

    def _clear(self) -> None:
        for tx_id, _ in self.rs.zscan_iter(self.name):
            self.drop(tx_id)

    def drop(self, tx_id: bytes) -> None:
        logger.info('Removing %s from pool ...', tx_id)
        self.rs.zrem(self.name, tx_id)

    def save(self, tx: Tx) -> None:
        logger.info('Updating record for tx %s ...', tx.tx_id)
        self.rs.set(tx.tx_id, tx.to_bytes())

    def fetch_next(self) -> Optional[Tx]:
        tx = None
        while tx is None and self.size > 0:
            tx_id = self.get_next_id()
            logger.debug('Received %s from pool', tx_id)
            tx = self.get(tx_id)
            if tx is None:
                logger.error('Received malformed tx %s. Going to remove ...')
                self.drop(tx_id)
        return tx

    def release(self, tx: Tx) -> None:
        logger.info('Releasing tx %s ...', tx.tx_id)
        pipe = self.rs.pipeline()
        pipe.set(tx.tx_id, tx.to_bytes())
        pipe.zrem(self.name, tx.tx_id)
        pipe.execute()
