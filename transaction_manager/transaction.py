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
import time

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .config import MAX_RESUBMIT_AMOUNT, GAS_MULTIPLIER

logger = logging.getLogger(__name__)


class InvalidFormatError(Exception):
    pass


class TxStatus(Enum):
    PROPOSED = 1
    SEEN = 2
    SENT = 3
    UNSENT = 4
    TIMEOUT = 5
    MINED = 6
    UNCONFIRMED = 7
    SUCCESS = 8
    FAILED = 9
    DROPPED = 10


@dataclass
class Tx:
    tx_id: str
    status: TxStatus
    score: int
    to: str
    hashes: List = field(default_factory=list)
    attempts: int = 0
    value: int = 0
    multiplier: Optional[float] = GAS_MULTIPLIER
    source: Optional[str] = None
    gas: Optional[int] = None
    chain_id: Optional[int] = None
    gas_price: Optional[int] = None
    nonce: Optional[int] = None
    data: Optional[Dict] = None
    tx_hash: Optional[str] = None
    sent_ts: Optional[int] = None

    @property
    def raw_id(self) -> bytes:
        return self.tx_id.encode('utf-8')

    def is_mined(self) -> bool:
        return self.status in (
            TxStatus.MINED,
            TxStatus.SUCCESS,
            TxStatus.FAILED
        )

    def is_completed(self) -> bool:
        return self.status in (
            TxStatus.SUCCESS,
            TxStatus.FAILED,
            TxStatus.DROPPED
        )

    def is_sent(self) -> bool:
        return self.tx_hash is not None

    def is_last_attempt(self) -> bool:
        return self.attempts > MAX_RESUBMIT_AMOUNT

    def set_as_completed(self, tx_hash: str, receipt_status: int) -> None:
        self.tx_hash = tx_hash
        if receipt_status == 1:
            self.status = TxStatus.SUCCESS
        else:
            self.status = TxStatus.FAILED

    def set_as_sent(self, tx_hash: str) -> None:
        self.status = TxStatus.SENT
        self.tx_hash = tx_hash
        self.sent_ts = int(time.time())
        self.hashes.append(tx_hash)

    @property
    def eth_tx(self) -> Dict:
        etx: Dict = {
            'from': self.source,
            'to': self.to,
            'value': self.value,
            'gasPrice': self.gas_price,
            'nonce': self.nonce,
            'chainId': self.chain_id,
        }
        if self.gas:
            etx.update({'gas': self.gas})
        if self.data:
            etx.update({'data': self.data})
        return etx

    def to_bytes(self) -> bytes:
        plain_tx = asdict(self)
        del plain_tx['tx_id']
        del plain_tx['gas_price']
        del plain_tx['source']
        plain_tx['status'] = self.status.name
        plain_tx['gasPrice'] = self.gas_price
        plain_tx['from'] = self.source
        return json.dumps(plain_tx, sort_keys=True).encode('utf-8')

    @classmethod
    def from_bytes(cls, tx_id: bytes, tx_bytes: bytes) -> 'Tx':
        logger.debug('Tx %s bytes %s', tx_id, tx_bytes)
        try:
            plain_tx = json.loads(tx_bytes.decode('utf-8'))
            plain_tx['tx_id'] = tx_id.decode('utf-8')
        except (json.decoder.JSONDecodeError, UnicodeError, TypeError):
            logger.error('Failed to make tx %s from bytes', tx_id)
            raise InvalidFormatError(f'Invalid record for {str(tx_id)}')

        try:
            status_name = plain_tx.get('status')
            plain_tx['status'] = TxStatus[status_name]
        except KeyError:
            logger.error('Tx %s has wrong status %s', tx_id, status_name)
            raise InvalidFormatError(f'No such status {status_name}')

        plain_tx['gas_price'] = plain_tx.get('gasPrice')
        plain_tx['chain_id'] = plain_tx.get('chainId')
        plain_tx['source'] = plain_tx.get('from')
        if 'chainId' in plain_tx:
            del plain_tx['chainId']
        if 'gasPrice' in plain_tx:
            del plain_tx['gasPrice']
        if 'from' in plain_tx:
            del plain_tx['from']
        if 'hashes' not in plain_tx:
            plain_tx['hashes'] = []
        try:
            tx = Tx(**plain_tx)
        except TypeError:
            logger.exception('Tx creation for %s errored', tx_id)
            raise InvalidFormatError(f'Missing fields for {str(tx_id)} record')
        return tx
