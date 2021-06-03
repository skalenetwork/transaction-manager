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

import os
import sys
from typing import Optional

REDIS_URI: str = 'redis://@127.0.0.1:6379'

SGX_URL: Optional[str] = 'https://127.0.0.1:1026'

ETH_PRIVATE_KEY: Optional[str] = None

ENDPOINT: str = 'http://127.0.0.1:8545'

GAS_MULTIPLIER: float = 1.8

NODE_DATA_PATH = '/skale_node_data'

CONFIRMATION_BLOCKS: int = 2

MAX_RESUBMIT_AMOUNT: int = 10

MAX_GAS_PRICE: int = 3 * 10 ** 9

BASE_WAITING_TIME: int = 10

GAS_PRICE_INC_PERCENT: int = 10

GRAD_GAS_PRICE_INC_PERCENT: int = 2

MAX_WAITING_TIME: int = 600  # TODO: determine value


for v in list(
    filter(
        lambda v: not v.startswith('__') and v in os.environ,
        globals()
    )
):
    type_ = type(getattr(sys.modules[__name__], v))
    if not isinstance(None, type_):
        casted = type_(os.environ[v])
    else:
        casted = os.environ[v]
    globals()[v] = casted
