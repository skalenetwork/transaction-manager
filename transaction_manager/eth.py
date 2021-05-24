""" Communicate with eth network """

import logging
from typing import Dict, Optional

from eth_typing.evm import ChecksumAddress
from web3 import Web3
from web3.types import TxParams

from .resources import w3 as gw3
from .config import GAS_MULTIPLIER

logger = logging.getLogger(__name__)


class Eth:
    def __init__(self, web3: Optional[Web3]) -> None:
        self.w3: Web3 = web3 or gw3

    @property
    def block_gas_limit(self) -> int:
        latest_block_number = self.w3.eth.blockNumber
        block = self.w3.eth.getBlock(latest_block_number)
        return block['gasLimit']

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
