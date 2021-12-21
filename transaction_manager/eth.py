#
#   -*- coding: utf-8 -*-
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
import time
from functools import cached_property
from typing import cast, Dict, Optional

from eth_typing.evm import ChecksumAddress, HexStr
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxParams

from .resources import w3 as gw3
from .config import (
    CONFIRMATION_BLOCKS,
    DISABLE_GAS_ESTIMATION,
    GAS_MULTIPLIER,
    AVG_GAS_PRICE_INC_PERCENT,
    MAX_WAITING_TIME
)
from .transaction import Tx

logger = logging.getLogger(__name__)


class BlockTimeoutError(TimeoutError):
    pass


class ReceiptTimeoutError(TransactionNotFound, TimeoutError):
    pass


def is_replacement_underpriced(err: Exception) -> bool:
    # TODO: IVD make sure it is still correct
    return isinstance(err, ValueError) and \
        isinstance(err.args[0], dict) and \
        err.args[0].get('message') == 'replacement transaction underpriced'


def is_nonce_too_low(err: Exception) -> bool:
    return isinstance(err, ValueError) and 'nonce' in err.args[0]['message']


class Eth:
    def __init__(self, web3: Optional[Web3] = None) -> None:
        self.w3: Web3 = web3 or gw3

    @property
    def block_gas_limit(self) -> int:
        latest_block_number = self.w3.eth.blockNumber
        block = self.w3.eth.getBlock(latest_block_number)
        return block['gasLimit']

    @cached_property
    def chain_id(self) -> int:
        return self.w3.eth.chainId

    def get_balance(self, address: ChecksumAddress) -> int:
        return self.w3.eth.getBalance(address)

    TX_ATTRS = [
        'from',
        'to',
        'value',
        'nonce',
        'chainId',
        'gas',
        'data',
        'gasPrice',
        'maxFeePerGas',
        'maxPriorityFeePerGas'
    ]

    @classmethod
    def convert_tx(cls, tx: Tx) -> Dict:
        # TODO: convert using classes
        raw_tx = tx.raw_tx
        etx = {attr: raw_tx[attr] for attr in cls.TX_ATTRS}
        if etx.get('maxPriorityFeePerGas') is not None or \
                etx.get('maxFeePerGas') is not None:
            etx['type'] = 2
            etx.pop('gasPrice', None)
        else:
            etx['type'] = 1
            etx.pop('maxPriorityFeePerGas', None)
            etx.pop('maxFeePerGas', None)

        if etx.get('gas') is None:
            etx.pop('gas')
        if etx.get('data') is None:
            etx.pop('data')
        return etx

    @property
    def avg_gas_price(self) -> int:
        return self.w3.eth.gasPrice * (100 + AVG_GAS_PRICE_INC_PERCENT) // 100

    def calculate_gas(self, tx: Tx) -> int:
        etx = self.convert_tx(tx)
        multiplier = tx.multiplier
        logger.info('IVD tx %s', etx)
        multiplier = multiplier or GAS_MULTIPLIER
        if DISABLE_GAS_ESTIMATION:
            return int(etx['gas'] * multiplier)

        logger.info('Estimating gas for %s', etx)
        estimated = self.w3.eth.estimateGas(
            cast(TxParams, etx),
            block_identifier='latest'
        )
        logger.info('Estimated gas: %s', estimated)
        gas = int(estimated * multiplier)
        logger.info('Multiplied gas: %s', gas)
        gas_limit = self.block_gas_limit
        if gas > gas_limit:
            logger.warning(
                'Estimated gas is to high. Defaulting to %s',
                gas_limit
            )
            gas = gas_limit
        return int(gas)

    def send_tx(self, signed_tx: Dict) -> str:
        tx_hash = self.w3.eth.sendRawTransaction(
            signed_tx['rawTransaction']
        ).hex()
        return tx_hash

    def get_nonce(self, address: ChecksumAddress) -> int:
        return self.w3.eth.getTransactionCount(address)

    def get_status(
        self,
        tx_hash: str,
        raise_err: bool = False
    ) -> int:
        try:
            receipt = self.w3.eth.getTransactionReceipt(cast(HexStr, tx_hash))
        except TransactionNotFound as e:
            if raise_err:
                raise e
            else:
                return -1
        logger.debug(f'Receipt for {tx_hash}: {receipt}')
        rstatus = receipt.get('status', -1)
        if rstatus < 0:
            logger.error('Receipt has no "status" field')
            return rstatus
        return rstatus

    def wait_for_blocks(
        self,
        amount: int = CONFIRMATION_BLOCKS,
        max_time: int = MAX_WAITING_TIME
    ) -> None:
        current_block = start_block = self.w3.eth.blockNumber
        current_ts = start_ts = time.time()
        while current_block - start_block < amount and \
                current_ts - start_ts < max_time:
            time.sleep(1)
            current_block = self.w3.eth.blockNumber
            current_ts = time.time()
        if current_block - start_block < amount:
            raise BlockTimeoutError(
                f'{amount} blocks has not been mined withing {max_time}'
            )

    def wait_for_receipt(
        self,
        tx_hash: str,
        max_time: int = MAX_WAITING_TIME,
    ) -> int:
        start_ts = time.time()
        rstatus = None
        while rstatus is None and time.time() - start_ts < max_time:
            try:
                rstatus = self.get_status(tx_hash, raise_err=True)
            except TransactionNotFound:
                time.sleep(1)

        if rstatus is None:
            raise ReceiptTimeoutError(f'No receipt after {max_time}')
        return rstatus
