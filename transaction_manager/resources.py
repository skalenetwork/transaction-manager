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

import logging

import redis
import statsd  # type: ignore
from skale.utils.web3_utils import get_endpoint, init_web3  # type: ignore
from web3 import Web3

from .config import (
    ALLOWED_TS_DIFF,
    LOCAL_SKALED_ENDPOINT_REDIS_KEY,
    REDIS_URI,
    STATSD_HOST,
    STATSD_PORT,
    get_node_settings,
)

logger = logging.getLogger(__name__)

cpool: redis.ConnectionPool = redis.ConnectionPool.from_url(REDIS_URI)
rs: redis.Redis = redis.Redis(connection_pool=cpool)
stdc: statsd.StatsClient = statsd.StatsClient(STATSD_HOST, STATSD_PORT)


def w3() -> Web3:
    endpoint = get_endpoint(endpoints())
    return init_web3(endpoint, ts_diff=ALLOWED_TS_DIFF)


def endpoints() -> list[str]:
    st = get_node_settings()
    eps = [str(st.endpoint)]
    local_skaled_endpoint = rs.get(LOCAL_SKALED_ENDPOINT_REDIS_KEY)
    if local_skaled_endpoint and isinstance(local_skaled_endpoint, bytes):
        local_endpoint_str = local_skaled_endpoint.decode('utf-8')
        logger.info(f'Found local skaled endpoint in Redis: {local_endpoint_str}')
        eps.insert(0, local_endpoint_str)
    logger.info(f'Returning a list of endpoints: {eps}')
    return eps
