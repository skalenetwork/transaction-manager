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
from urllib.parse import urlparse

from configs import NODE_DATA_PATH

SGX_SERVER_URL = os.getenv('SGX_SERVER_URL')

SGX_URL = urlparse(SGX_SERVER_URL)
SGX_HTTPS_ENABLED = SGX_URL.scheme == 'https'

SGX_CERTIFICATES_DIR_NAME = os.getenv('SGX_CERTIFICATES_DIR_NAME')

if SGX_HTTPS_ENABLED:
    if SGX_CERTIFICATES_DIR_NAME:
        SGX_CERTIFICATES_FOLDER = os.path.join(
            NODE_DATA_PATH,
            SGX_CERTIFICATES_DIR_NAME
        )
    else:
        SGX_CERTIFICATES_DIR = os.getenv('SGX_CERTIFICATES_DIR')
else:
    SGX_CERTIFICATES_FOLDER = None
