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
import threading
from skale.utils.web3_utils import get_eth_nonce

logger = logging.getLogger(__name__)
threadLock = threading.Lock()


class NonceManager():
    def __init__(self, skale, wallet):
        self.skale = skale
        self.wallet = wallet
        self.request_network_nonce()

    def get_nonce(self):
        return self.__nonce

    def increment_nonce(self):
        with threadLock:
            self.__nonce += 1
            logger.info(f'Incremented nonce: {self.__nonce}')

    def transaction_nonce(self):
        nonce = self.get_nonce()
        self.increment_nonce()
        return nonce

    def request_network_nonce(self):
        self.__nonce = get_eth_nonce(self.skale.web3, self.wallet['address'])
        logger.info(f'Requested nonce from the network: {self.__nonce}')
