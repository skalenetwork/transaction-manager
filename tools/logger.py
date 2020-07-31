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

import sys
import logging
from logging import Formatter, StreamHandler
from logging.handlers import RotatingFileHandler

from configs.logs import (TM_LOG_PATH, TM_DEBUG_LOG_PATH, LOG_FILE_SIZE_BYTES, LOG_BACKUP_COUNT,
                          LOG_FORMAT)


def init_logger(log_file_path, debug_file_path=None):
    handlers = []

    formatter = Formatter(LOG_FORMAT)
    f_handler = RotatingFileHandler(log_file_path, maxBytes=LOG_FILE_SIZE_BYTES,
                                    backupCount=LOG_BACKUP_COUNT)

    f_handler.setFormatter(formatter)
    f_handler.setLevel(logging.INFO)
    handlers.append(f_handler)

    stream_handler = StreamHandler(sys.stderr)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    handlers.append(stream_handler)

    if debug_file_path:
        f_handler_debug = RotatingFileHandler(debug_file_path,
                                              maxBytes=LOG_FILE_SIZE_BYTES,
                                              backupCount=LOG_BACKUP_COUNT)
        f_handler_debug.setFormatter(formatter)
        f_handler_debug.setLevel(logging.DEBUG)
        handlers.append(f_handler_debug)

    logging.basicConfig(level=logging.DEBUG, handlers=handlers)


def init_tm_logger():
    init_logger(TM_LOG_PATH, TM_DEBUG_LOG_PATH)
