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

import redis

from skale.utils.web3_utils import init_web3  # type: ignore
from skale.wallets import BaseWallet, Web3Wallet  # type: ignore
from web3 import Web3

from .config import ENDPOINT, ETH_PRIVATE_KEY, REDIS_URI

# TODO: IVD check out options to configure
cpool: redis.ConnectionPool = redis.ConnectionPool.from_url(REDIS_URI)
rs: redis.Redis = redis.Redis(connection_pool=cpool)
# TODO: IVD check out options to configure
w3: Web3 = init_web3(ENDPOINT)

wallet: BaseWallet = Web3Wallet(ETH_PRIVATE_KEY, w3)
