#   -*- coding: utf-8 -*-
#
#   This file is part of SKALE Transaction Manager
#
#   Copyright (C) 2019 SKALE Labs
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
from time import sleep
from skale.utils.web3_utils import get_eth_nonce
from skale.utils.account_tools import send_ether
from skale.wallets import BaseWallet
from web3 import Web3

logger = logging.getLogger(__name__)


class NonceManager:
    def __init__(self, web3: Web3, wallet: BaseWallet,
                 wait_for_blocks: bool = True) -> None:
        self.web3 = web3
        self.wallet = wallet
        if wait_for_blocks:
            self.wait_for_blocks()
        self._nonce = self.request_nonce()

    @property
    def nonce(self) -> int:
        return self.ensure_nonce()

    def ensure_nonce(self) -> int:
        logger.info('Running ensure_nonce...')
        local_nonce = self._nonce
        network_nonce = self.request_nonce()
        logger.info(f'Local nonce: {local_nonce}, network nonce: {network_nonce}')
        self._nonce = max(local_nonce, network_nonce)
        return self._nonce

    def request_nonce(self) -> int:
        logger.info('Running request_nonce...')
        address = self.wallet.address
        logger.info(f'Got wallet address: {address}, going to request eth nonce')
        eth_nonce = get_eth_nonce(self.web3, address)
        logger.info(f'Got network nonce for {address}: {eth_nonce}')
        return eth_nonce

    def healthcheck(self) -> int:
        logger.info('Running healthcheck...')
        receipt = send_ether(
            web3=self.web3,
            sender_wallet=self.wallet,
            receiver_account=self.wallet.address,
            amount=0
        )
        res = receipt['status'] == 1
        if res:
            logger.info('Healthcheck transaction passed')
        else:
            logger.error(f'Healthcheck transaction failed! Tx: {receipt["transactionHash"]}')
        return res

    def fix_nonce(self) -> None:
        self.wait_for_blocks()
        network_nonce = self.request_nonce()
        logger.info(f'Resetting nonce to the network value: {network_nonce}')
        self._nonce = network_nonce
        self.healthcheck()

    def increment(self, request_from_network: bool = False) -> None:
        logger.info(f'Incrementing nonce from: {self.nonce}...')
        if request_from_network:
            self.ensure_nonce()
        self._nonce += 1
        logger.info(f'Incremented nonce: {self.nonce}')

    def wait_for_blocks(self, timeout: int = 5, blocks_to_wait: int = 5):
        current_block = start_block = self.web3.eth.blockNumber
        logger.info(
            f'Current block number is {current_block}, '
            f'waiting for {blocks_to_wait} blocks to be mined'
        )
        while current_block < start_block + blocks_to_wait:
            new_block = self.web3.eth.blockNumber
            if new_block > current_block:
                logger.info(f'{new_block} is mined')
                current_block = new_block
            sleep(timeout)
