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

from .config import (
    DEFAULT_ID_LEN,
    GAS_MULTIPLIER,
    IMA_ID_SUFFIX,
    MAX_RESUBMIT_AMOUNT
)

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
class Fee:
    gas_price: Optional[int] = None
    max_fee_per_gas: Optional[int] = None
    max_priority_fee_per_gas: Optional[int] = None


@dataclass
class Tx:
    tx_id: str
    status: TxStatus
    score: int
    to: str
    fee: Fee
    hashes: List = field(default_factory=list)
    attempts: int = 0
    value: int = 0
    multiplier: Optional[float] = GAS_MULTIPLIER
    source: Optional[str] = None
    gas: Optional[int] = None
    chain_id: Optional[int] = None
    nonce: Optional[int] = None
    data: Optional[Dict] = None
    tx_hash: Optional[str] = None
    sent_ts: Optional[int] = None
    method: Optional[str] = None
    meta: Optional[Dict] = None

    MAPPED_ATTR = {
        'chainId': 'chain_id',
        'gasPrice': 'gas_price',
        'maxFeePerGas': 'max_fee_per_gas',
        'maxPriorityFeePerGas': 'max_priority_fee_per_gas',
        'from': 'source'
    }

    def __post_init__(self):
        if isinstance(self.fee, dict):
            self.fee = Fee(**self.fee)

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

    def set_as_mined(self) -> None:
        self.status = TxStatus.MINED

    def set_as_sent(self, tx_hash: str) -> None:
        self.status = TxStatus.SENT
        self.tx_hash = tx_hash
        self.sent_ts = int(time.time())
        self.hashes.append(tx_hash)

    def set_as_dropped(self) -> None:
        self.status = TxStatus.DROPPED

    def is_sent_by_ima(self) -> bool:
        return len(self.tx_id) > DEFAULT_ID_LEN and self.tx_id[-2:] == IMA_ID_SUFFIX

    @property
    def raw_tx(self) -> Dict:
        raw_tx = asdict(self)
        raw_tx['status'] = self.status.name
        raw_tx.update(asdict(self.fee))
        del raw_tx['fee']
        for original, mapped in self.MAPPED_ATTR.items():
            if mapped in raw_tx:
                raw_tx[original] = raw_tx[mapped]
                del raw_tx[mapped]
        return raw_tx

    def to_bytes(self) -> bytes:
        return json.dumps(self.raw_tx, sort_keys=True).encode('utf-8')

    @classmethod
    def _extract_fee(self, raw_tx: Dict) -> Fee:
        gas_price = raw_tx.pop('gas_price', None)
        max_fee_per_gas = raw_tx.pop('max_fee_per_gas', None)
        max_priority_fee_per_gas = raw_tx.pop('max_priority_fee_per_gas', None)
        return Fee(gas_price, max_fee_per_gas, max_priority_fee_per_gas)

    @classmethod
    def from_bytes(cls, tx_id: bytes, tx_bytes: bytes) -> 'Tx':
        logger.debug('Tx %s bytes %s', tx_id, tx_bytes)
        try:
            raw_tx = json.loads(tx_bytes.decode('utf-8'))
            raw_tx['tx_id'] = tx_id.decode('utf-8')
        except (json.decoder.JSONDecodeError, UnicodeError, TypeError):
            logger.error('Failed to make tx %s from bytes', tx_id)
            raise InvalidFormatError(f'Invalid record for {str(tx_id)}')

        try:
            status_name = raw_tx.get('status')
            raw_tx['status'] = TxStatus[status_name]
        except KeyError:
            logger.error('Tx %s has wrong status %s', tx_id, status_name)
            raise InvalidFormatError(f'No such status {status_name}')

        for original, mapped in cls.MAPPED_ATTR.items():
            if original in raw_tx:
                raw_tx[mapped] = raw_tx[original]
                del raw_tx[original]

        raw_tx['fee'] = cls._extract_fee(raw_tx)
        raw_tx['hashes'] = raw_tx.get('hashes') or []
        raw_tx.pop('type', None)
        try:
            tx = Tx(**raw_tx)
        except TypeError:
            logger.exception('Tx creation for %s errored', tx_id)
            raise InvalidFormatError(f'Missing fields for {str(tx_id)} record')
        return tx


@dataclass
class Attempt:
    tx_id: str
    nonce: int
    index: int
    fee: Fee
    wait_time: int
    gas: Optional[int] = None

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
