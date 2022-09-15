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

from .config import NODE_DATA_PATH


LOG_FOLDER = os.path.join(NODE_DATA_PATH, 'log')
TM_LOG_PATH = os.path.join(LOG_FOLDER, 'tm.log')
TM_DEBUG_LOG_PATH = os.path.join(LOG_FOLDER, 'debug_tm.log')

LOG_FILE_SIZE_MB = 100
LOG_FILE_SIZE_BYTES = LOG_FILE_SIZE_MB * 1000000

LOG_BACKUP_COUNT = 3

LOG_FORMAT = '%(asctime)s [%(levelname)s] [%(module)s:%(lineno)d] %(message)s'  # noqa


HIDING_PATTERNS = [
    r'NEK\:\w+',
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # noqa
    r'ws[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+',  # noqa
    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'  # noqa
]


class HidingFormatter(Formatter):
    def __init__(self, base_formatter: Formatter, patterns: List[str]) -> None:
        self.base_formatter: Formatter = base_formatter
        self._patterns: List[str] = patterns

    @classmethod
    def convert_match_to_sha3(cls, match) -> str:
        return hashlib.sha3_256(match.group(0).encode('utf-8')).digest().hex()

    def format(self, record):
        msg = self.base_formatter.format(record)
        for pattern in self._patterns:
            pat = re.compile(pattern)
            msg = pat.sub(self.convert_match_to_sha3, msg)
        return msg

    def __getattr__(self, attr):
        return getattr(self.base_formatter, attr)


def init_logger() -> None:
    handlers: List[Handler] = []

    base_formatter = Formatter(LOG_FORMAT)
    formatter = HidingFormatter(base_formatter, HIDING_PATTERNS)

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

    logging.basicConfig(level=logging.DEBUG, handlers=handlers)
