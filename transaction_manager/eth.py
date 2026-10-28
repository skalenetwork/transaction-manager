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
from typing import Dict, Optional, cast

from eth_account.datastructures import SignedTransaction
from eth_typing.evm import HexStr
from web3 import Web3
from web3.exceptions import ContractLogicError, TransactionNotFound, Web3RPCError
from web3.types import FeeHistory, TxParams

from .config import (
    CONFIRMATION_BLOCKS,
    DEFAULT_GAS_LIMIT,
    DISABLE_GAS_ESTIMATION,
    GAS_MULTIPLIER,
    MAX_WAITING_TIME,
    TARGET_REWARD_PERCENTILE,
)
from .resources import stdc
from .resources import w3 as gw3
from .structures import Tx

logger = logging.getLogger(__name__)


class BlockTimeoutError(TimeoutError):
    pass


class ReceiptTimeoutError(TransactionNotFound, TimeoutError):
    pass


class EstimateGasRevertError(Exception):
    pass


def is_replacement_underpriced(err: Exception) -> bool:
    return (
        isinstance(err, Web3RPCError)
        and err.rpc_response is not None
        and err.rpc_response['error']['message'] == 'replacement transaction underpriced'
    )


class Eth:
    def __init__(self, web3: Optional[Web3] = None) -> None:
        self.w3: Web3 = web3 or gw3()

    @property
    def block_gas_limit(self) -> int:
        latest_block_number = self.w3.eth.block_number
        block = self.w3.eth.get_block(latest_block_number)
        return block['gasLimit']

    @cached_property
    def chain_id(self) -> int:
        with stdc.timer('tm.chain_id_request'):
            return self.w3.eth.chain_id

    def get_balance(self, address: str) -> int:
        checksum_addres = self.w3.to_checksum_address(address)
        return self.w3.eth.get_balance(checksum_addres)

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
        'maxPriorityFeePerGas',
    ]

    def get_fee_history(self) -> FeeHistory:
        return self.w3.eth.fee_history(1, 'latest', [50, TARGET_REWARD_PERCENTILE])

    def get_estimated_base_fee(self, history: Optional[FeeHistory] = None) -> int:
        history = history or self.get_fee_history()
        return history['baseFeePerGas'][-1]

    def get_p60_tip(self, history: Optional[FeeHistory] = None) -> int:
        history = history or self.get_fee_history()
        return history['reward'][0][-1]

    @classmethod
    def convert_tx(cls, tx: Tx) -> TxParams:
        raw_tx = tx.raw_tx
        etx = {attr: raw_tx[attr] for attr in cls.TX_ATTRS}
        if etx.get('maxPriorityFeePerGas') is not None or etx.get('maxFeePerGas') is not None:
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
        return cast(TxParams, etx)

    def calculate_gas(self, tx: Tx) -> int:
        etx = self.convert_tx(tx)
        multiplier = tx.multiplier
        multiplier = multiplier or GAS_MULTIPLIER
        if DISABLE_GAS_ESTIMATION:
            return int(etx.get('gas', DEFAULT_GAS_LIMIT) * multiplier)

        logger.info('Estimating gas for %s', etx)

        try:
            estimated = self.w3.eth.estimate_gas(etx, block_identifier='latest')
        except ContractLogicError as e:
            logger.exception('Estimate gas reverted with ContractLogicError')
            raise EstimateGasRevertError(e)

        logger.info('eth_estimateGas returned: %s of gas', estimated)
        gas = int(estimated * multiplier)
        logger.info('Multiplied gas: %s', gas)
        gas_limit = self.block_gas_limit
        if gas > gas_limit:
            logger.warning('Estimated gas is to high. Defaulting to %s', gas_limit)
            gas = gas_limit
        gas = int(gas)
        logger.info('Estimation result %s of gas', gas)
        return gas

    def send_tx(self, signed_tx: SignedTransaction) -> str:
        return self.w3.eth.send_raw_transaction(signed_tx.raw_transaction).hex()

    def get_nonce(self, address: str) -> int:
        checksum_address = self.w3.to_checksum_address(address)
        return self.w3.eth.get_transaction_count(checksum_address)

    def wait_for_blocks(
        self,
        amount: int = CONFIRMATION_BLOCKS,
        max_time: int = MAX_WAITING_TIME,
        start_block: Optional[int] = None,
    ) -> None:
        current_block = self.w3.eth.block_number
        start_block = start_block or current_block
        current_ts = start_ts = time.time()
        while current_block - start_block < amount and current_ts - start_ts < max_time:
            time.sleep(1)
            current_block = self.w3.eth.block_number
            current_ts = time.time()
        if current_block - start_block < amount:
            raise BlockTimeoutError(f'{amount} blocks has not been mined withing {max_time}')

    def wait_for_receipt(
        self,
        tx_hash: str,
        max_time: int = MAX_WAITING_TIME,
    ) -> int:
        start_ts = time.time()
        rstatus = -1
        while rstatus == -1 and time.time() - start_ts < max_time:
            rstatus = self.get_status(tx_hash)
            if rstatus == -1:
                time.sleep(1)

        if rstatus == -1:
            raise ReceiptTimeoutError(f'No receipt after {max_time}')
        return rstatus

    def get_receipt(self, tx_hash: str) -> Optional[Dict]:
        receipt = None
        try:
            casted_hash = cast(HexStr, tx_hash)
            receipt = self.w3.eth.get_transaction_receipt(casted_hash)
        except TransactionNotFound:
            pass
        return cast(Dict, receipt)

    def get_tx_block(self, tx_hash: str) -> int:
        receipt = self.get_receipt(tx_hash)
        if receipt is None:
            return -1
        return cast(int, receipt.get('blockNumber'))

    def get_status(self, tx_hash: str) -> int:
        receipt = self.get_receipt(tx_hash)
        logger.debug('Receipt for %s: %s', tx_hash, receipt)
        if receipt is None:
            return -1
        rstatus = receipt.get('status', -1)
        if rstatus < 0:
            logger.error('Receipt has no "status" field')
            return rstatus
        return rstatus
