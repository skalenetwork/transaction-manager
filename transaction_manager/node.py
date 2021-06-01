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
import os

from .config import NODE_DATA_PATH

NODE_CONFIG_FILEPATH = os.path.join(NODE_DATA_PATH, 'node_config.json')


def is_config_created() -> bool:
    return os.path.isfile(NODE_CONFIG_FILEPATH)


def get_sgx_keyname() -> str:
    with open(NODE_CONFIG_FILEPATH, encoding='utf-8') as data_file:
        config = json.loads(data_file.read())
    return config['sgx_key_name']
