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
import logging
import json
from http import HTTPStatus
from flask import Response
from time import sleep

from skale.wallets import Web3Wallet
from configs import LOCAL_WALLET_FILEPATH, DEFAULT_SLEEP_TIMEOUT


logger = logging.getLogger(__name__)


def construct_response(status, data):
    return Response(
        response=json.dumps(data),
        status=status,
        mimetype='application/json'
    )


def construct_err_response(status, err):
    return construct_response(status, {'data': None, 'error': str(err)})


def construct_ok_response(data=None):
    return construct_response(HTTPStatus.OK, {'data': data, 'error': None})


def get_software_wallet():
    with open(LOCAL_WALLET_FILEPATH, encoding='utf-8') as data_file:
        return json.loads(data_file.read())


def init_wallet(web3):
    while not os.path.isfile(LOCAL_WALLET_FILEPATH):
        logger.info(f'Waiting for the {LOCAL_WALLET_FILEPATH} to be created...')
        sleep(DEFAULT_SLEEP_TIMEOUT)
    with open(LOCAL_WALLET_FILEPATH, encoding='utf-8') as data_file:
        wallet_data = json.loads(data_file.read())
    return Web3Wallet(wallet_data['private_key'], web3)
