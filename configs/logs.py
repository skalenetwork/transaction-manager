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

import os
from configs import NODE_DATA_PATH

LOG_DIR_NAME = 'log'
LOG_DIR = os.path.join(NODE_DATA_PATH, LOG_DIR_NAME)

TM_LOG_FILENAME = 'tm.log'
TM_LOG_PATH = os.path.join(LOG_DIR, TM_LOG_FILENAME)

TM_DEBUG_LOG_FILENAME = 'debug_tm.log'
TM_DEBUG_LOG_PATH = os.path.join(LOG_DIR, TM_DEBUG_LOG_FILENAME)

LOG_FILE_SIZE_MB = 100
LOG_FILE_SIZE_BYTES = LOG_FILE_SIZE_MB * 1000000

LOG_BACKUP_COUNT = 3

LOG_FORMAT = '[%(asctime)s %(levelname)s] %(name)s - %(message)s'

STDERR_LOG = os.getenv('STDOUT_LOG', 'True') == 'True'
