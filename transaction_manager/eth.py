""" Communicate with eth network """

import logging
import time
from typing import Dict, Optional

from eth_typing.evm import ChecksumAddress, HexStr
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxParams, TxReceipt

from .resources import w3 as gw3
from .config import GAS_MULTIPLIER

logger = logging.getLogger(__name__)

MAX_WAITING_TIME = 60


class BlockTimeoutError(TimeoutError):
    pass


class ReceiptTimeoutError(TransactionNotFound, TimeoutError):
    pass


class Eth:
    def __init__(self, web3: Optional[Web3]) -> None:
        self.w3: Web3 = web3 or gw3

    @property
    def block_gas_limit(self) -> int:
        latest_block_number = self.w3.eth.blockNumber
        block = self.w3.eth.getBlock(latest_block_number)
        return block['gasLimit']

    def balance(self, address: ChecksumAddress) -> int:
        return self.w3.eth.getBalance(address)

    def calculate_gas(self, tx: TxParams) -> int:
        estimated = self.w3.eth.estimateGas(tx)
        gas = int(GAS_MULTIPLIER * estimated)
        gas_limit = self.block_gas_limit
        if gas < gas_limit:
            logger.warning(
                f'Estimated gas is to high. Defaulting to {gas_limit}'
            )
            gas = self.block_gas_limit
        return gas

    def send_tx(self, signed_tx: Dict) -> str:
        return self.w3.eth.sendRawTransaction(
            signed_tx['rawTransaction']
        ).hex()

    def get_nonce(self, address: ChecksumAddress) -> int:
        return self.w3.eth.getTransactionCount(address)

    def wait_for_blocks(
        self,
        amount: int,
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
        tx_hash: HexStr,
        max_time: int = MAX_WAITING_TIME
    ) -> TxReceipt:

        start_ts = time.time()
        receipt = None
        while time.time() - start_ts < max_time:
            try:
                receipt = self.w3.eth.getTransactionReceipt(tx_hash)
            except TransactionNotFound:
                time.sleep(1)
        if not receipt:
            raise ReceiptTimeoutError(
                f'Transaction is not mined withing {max_time}'
            )
        return receipt
