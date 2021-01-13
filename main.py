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

import json
import logging
import threading
from http import HTTPStatus

from flask import Flask, request
from werkzeug.exceptions import InternalServerError
from skale.utils.web3_utils import init_web3

from configs import ENDPOINT
from configs.flask import FLASK_APP_HOST, FLASK_APP_PORT, FLASK_DEBUG_MODE
from core import sign_and_send

from tools.logger import init_tm_logger
from tools.str_formatters import arguments_list_string
from tools.helper import (
    construct_ok_response, construct_err_response, init_wallet
)


init_tm_logger()

logger = logging.getLogger(__name__)
thread_lock = threading.Lock()

app = Flask(__name__)
app.port = FLASK_APP_PORT
app.host = FLASK_APP_HOST
app.use_reloader = False

web3 = init_web3(ENDPOINT)
wallet = init_wallet(web3)


@app.errorhandler(InternalServerError)
def handle_500(e):
    original = getattr(e, "original_exception", None)
    return construct_err_response(status=500, err=original)


@app.route('/sign-and-send', methods=['POST'])
def _sign_and_send():
    logger.debug(request)
    plain_tx_data = request.json.get('transaction_dict')
    tx_data = json.loads(plain_tx_data)
    thread_id = threading.get_ident()
    logger.info(f'thread_id {thread_id} waiting for the lock')
    with thread_lock:
        logger.info(f'thread_id {thread_id} got the lock')
        tx_hash, error = sign_and_send(web3, wallet, tx_data)
        if error is None:
            return construct_ok_response({'transaction_hash': tx_hash})
        else:
            return construct_err_response(HTTPStatus.BAD_REQUEST, error)


@app.route('/', methods=['GET'])
def index():
    return construct_ok_response({'status': 'ok'})


def main():
    logger.info(arguments_list_string({
        'Ethereum RPC endpoint': ENDPOINT}, 'Starting Transaction Manager'))
    app.run(debug=FLASK_DEBUG_MODE, port=FLASK_APP_PORT,
            host=FLASK_APP_HOST, use_reloader=False)


if __name__ == '__main__':
    main()
