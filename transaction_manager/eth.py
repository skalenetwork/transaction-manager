""" Communicate with eth network """

import logging
import time
from functools import cached_property
from typing import cast, Dict, Optional

from eth_typing.evm import ChecksumAddress, HexStr
from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.types import TxParams

from .resources import w3 as gw3
from .config import GAS_MULTIPLIER

logger = logging.getLogger(__name__)

MAX_WAITING_TIME = 500


class BlockTimeoutError(TimeoutError):
    pass


class ReceiptTimeoutError(TransactionNotFound, TimeoutError):
    pass


def is_replacement_underpriced(err: Exception) -> bool:
    return isinstance(err, ValueError) and \
        err.args[0]['message'] == 'replacement transaction underpriced'


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

    @property
    def avg_gas_price(self) -> int:
        return self.w3.eth.gasPrice

    def calculate_gas(self, tx: Dict) -> int:
        estimated = self.w3.eth.estimateGas(cast(TxParams, tx))
        gas = int(GAS_MULTIPLIER * estimated)
        gas_limit = self.block_gas_limit
        if gas < gas_limit:
            logger.warning(
                f'Estimated gas is to high. Defaulting to {gas_limit}'
            )
            gas = self.block_gas_limit
        return gas

    def send_tx(self, signed_tx: Dict) -> str:
        tx_hash = self.w3.eth.sendRawTransaction(
            signed_tx['rawTransaction']
        ).hex()
        return tx_hash

    def get_nonce(self, address: ChecksumAddress) -> int:
        return self.w3.eth.getTransactionCount(address)

    def get_receipt(
        self,
        tx_hash: str,
        raise_err: bool = False
    ) -> Optional[Dict]:
        receipt = None
        try:
            receipt = self.w3.eth.getTransactionReceipt(cast(HexStr, tx_hash))
        except TransactionNotFound as e:
            if raise_err:
                raise e
        return cast(Optional[Dict], receipt)

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
        tx_hash: str,
        max_time: int = MAX_WAITING_TIME
    ) -> Dict:
        start_ts = time.time()
        receipt = None
        while time.time() - start_ts < max_time:
            try:
                self.get_receipt(tx_hash, raise_err=True)
            except TransactionNotFound:
                time.sleep(1)
        if not receipt:
            raise ReceiptTimeoutError(
                f'Transaction is not mined withing {max_time}'
            )
        return receipt
