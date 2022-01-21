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

import json
import logging
import os
import time

from typing import Optional

from .config import NODE_DATA_PATH

logger = logging.getLogger(__name__)

NODE_CONFIG_FILEPATH = os.path.join(NODE_DATA_PATH, 'node_config.json')


def is_config_created() -> bool:
    return os.path.isfile(NODE_CONFIG_FILEPATH)


def get_sgx_keyname(config_filepath: Optional[str] = None) -> str:
    config_filepath = config_filepath or NODE_CONFIG_FILEPATH
    with open(config_filepath, encoding='utf-8') as data_file:
        config = json.loads(data_file.read())
    return config['sgx_key_name']


def wait_for_sgx_keyname(config_filepath: Optional[str] = None) -> str:
    config_filepath = config_filepath or NODE_CONFIG_FILEPATH
    cnt = 0
    while not os.path.isfile(config_filepath):
        if cnt < 5:
            logger.info('No such file %s. Waiting ...', config_filepath)
        time.sleep(3)
        cnt += 1
    return get_sgx_keyname(config_filepath)
