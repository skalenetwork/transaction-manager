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

logger = logging.getLogger(__name__)


class NonceManager:
    def __init__(self, skale, wallet):
        self.skale = skale
        self.wallet = wallet
        self.wait_for_blocks()
        self.__nonce = self.request_nonce()

    @property
    def nonce(self):
        return self.ensure_nonce()

    def ensure_nonce(self):
        local_nonce = self.__nonce
        network_nonce = self.request_nonce()
        logger.debug(f'Local nonce: {local_nonce}, network nonce: {network_nonce}')
        self.__nonce = max(local_nonce, network_nonce)
        return self.__nonce

    def request_nonce(self):
        address = self.wallet.address
        eth_nonce = get_eth_nonce(self.skale.web3, address)
        logger.debug(f'Got network nonce for {address}: {eth_nonce}')
        return eth_nonce

    def healthcheck(self):
        logger.debug('Running healthcheck...')
        receipt = send_ether(
            web3=self.skale.web3,
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

    def fix_nonce(self):
        self.wait_for_blocks()
        network_nonce = self.request_nonce()
        logger.info(f'Resetting nonce to the network value: {network_nonce}')
        self.__nonce = network_nonce
        self.healthcheck()

    def increment(self):
        logger.info(f'Incrementing nonce from: {self.nonce}...')
        self.ensure_nonce()
        self.__nonce += 1
        logger.info(f'Incremented nonce: {self.nonce}')

    def wait_for_blocks(self, timeout=5, blocks_to_wait=5):
        current_block = start_block = self.skale.web3.eth.blockNumber
        logger.info(
            f'Current block number is {current_block}, '
            f'waiting for {blocks_to_wait} blocks to be mined'
        )
        while current_block < start_block + blocks_to_wait:
            new_block = self.skale.web3.eth.blockNumber
            if new_block > current_block:
                logger.info(f'{new_block} is mined')
                current_block = new_block
            sleep(timeout)
