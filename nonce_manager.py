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
from skale.utils.web3_utils import get_eth_nonce

logger = logging.getLogger(__name__)


class NonceManager:
    def __init__(self, skale, wallet):
        self.skale = skale
        self.wallet = wallet
        self.wait_for_the_next_block()
        self.nonce = self.request_nonce()
        logger.info(f'Requested nonce from the network: {self.nonce}')

    def request_nonce(self):
        return get_eth_nonce(self.skale.web3, self.wallet.address)

    def update(self):
        logger.info(f'Updating nonce. Current nonce: {self.nonce}')
        self.nonce = max(self.nonce, self.request_nonce())
        logger.info(f'Nonce is updated. Current nonce: {self.nonce}')

    def increment(self):
        logger.info('Incrementing nonce from: {self.nonce} ...')
        self.update()
        self.nonce += 1
        logger.info(f'Incremented nonce: {self.nonce}')

    def wait_for_the_next_block(self):
        block_number = next_block = self.skale.web3.eth.blockNumber
        logger.info(f'Current block number is {block_number}, waiting for the next block')
        while next_block <= block_number:
            next_block = self.skale.web3.eth.blockNumber
        logger.info(f'Next block is mined: {next_block}.')
