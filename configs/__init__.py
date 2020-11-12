#   -*- coding: utf-8 -*-
#
#   This file is part of SKALE  Transaction Manager
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

import os
from configs.flask import FLASK_DEBUG_MODE

LONG_LINE = '=' * 100

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

SKALE_DIR_HOST = os.environ['SKALE_DIR_HOST']
NODE_DATA_PATH_HOST = os.path.join(SKALE_DIR_HOST, 'node_data')

if FLASK_DEBUG_MODE:
    SKALE_VOLUME_PATH = SKALE_DIR_HOST
    NODE_DATA_PATH = NODE_DATA_PATH_HOST
else:
    SKALE_VOLUME_PATH = '/skale_vol'
    NODE_DATA_PATH = '/skale_node_data'

NODE_CONFIG_FILENAME = 'node_config.json'
NODE_CONFIG_FILEPATH = os.path.join(NODE_DATA_PATH, NODE_CONFIG_FILENAME)

DEFAULT_SLEEP_TIMEOUT = 5

SGX_KEY_NAME_RETRIES = 30
SGX_KEY_NAME_TIMEOUT = 20

BLOCKS_TO_WAIT = os.getenv('BLOCKS_TO_WAIT', 5)
