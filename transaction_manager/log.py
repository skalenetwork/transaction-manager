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

import hashlib
import logging
import os
import re
import sys
from logging import Formatter, Handler, StreamHandler
from logging.handlers import RotatingFileHandler
from typing import List
from urllib.parse import urlparse

from .config import ENDPOINT, NODE_DATA_PATH, SGX_URL


LOG_FOLDER = os.path.join(NODE_DATA_PATH, 'log')
TM_LOG_PATH = os.path.join(LOG_FOLDER, 'tm.log')
TM_DEBUG_LOG_PATH = os.path.join(LOG_FOLDER, 'debug_tm.log')

LOG_FILE_SIZE_MB = 100
LOG_FILE_SIZE_BYTES = LOG_FILE_SIZE_MB * 1000000

LOG_BACKUP_COUNT = 3

LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(module)s:%(lineno)d] %(message)s'  # noqa


def compose_hiding_patterns():
    sgx_ip = urlparse(SGX_URL).hostname
    eth_ip = urlparse(ENDPOINT).hostname
    return {
        rf'{sgx_ip}': '[SGX_IP]',
        rf'{eth_ip}': '[ETH_IP]',
        r'NEK\:\w+': '[SGX_KEY]'
    }


class HidingFormatter(Formatter):
    def __init__(self, base_formatter: Formatter, patterns: dict) -> None:
        self.base_formatter: Formatter = base_formatter
        self._patterns: dict = patterns

    @classmethod
    def convert_match_to_sha3(cls, match) -> str:
        return hashlib.sha3_256(match.group(0).encode('utf-8')).digest().hex()

    def _filter_sensitive(self, msg):
        for match, replacement in self._patterns.items():
            pat = re.compile(match)
            msg = pat.sub(replacement, msg)
        return msg

    def format(self, record):
        msg = self.base_formatter.format(record)
        return self._filter_sensitive(msg)

    def formatException(self, exc_info):
        msg = self.base_formatter.formatException(exc_info)
        return self._filter_sensitive(msg)

    def formatStack(self, stack_info):
        msg = self.base_formatter.formatStack(stack_info)
        return self._filter_sensitive(msg)

    def __getattr__(self, attr):
        return getattr(self.base_formatter, attr)


def init_logger() -> None:
    handlers: List[Handler] = []

    base_formatter = Formatter(LOG_FORMAT)
    hiding_patterns = compose_hiding_patterns()
    formatter = HidingFormatter(base_formatter, hiding_patterns)

    f_handler = RotatingFileHandler(
        TM_LOG_PATH,
        maxBytes=LOG_FILE_SIZE_BYTES,
        backupCount=LOG_BACKUP_COUNT
    )
    f_handler.setFormatter(formatter)
    f_handler.setLevel(logging.INFO)
    handlers.append(f_handler)

    stream_handler = StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    handlers.append(stream_handler)

    f_handler_debug = RotatingFileHandler(
        TM_DEBUG_LOG_PATH,
        maxBytes=LOG_FILE_SIZE_BYTES,
        backupCount=LOG_BACKUP_COUNT
    )
    f_handler_debug.setFormatter(formatter)
    f_handler_debug.setLevel(logging.DEBUG)
    handlers.append(f_handler_debug)

    logging.basicConfig(level=logging.INFO, handlers=handlers)
