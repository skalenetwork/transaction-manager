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
from skale import Skale
from skale.utils.web3_utils import init_web3

from nonce_manager import NonceManager
from core import sign_and_send

from tools.logger import init_tm_logger
from tools.str_formatters import arguments_list_string
from tools.helper import construct_ok_response, construct_err_response, init_wallet

from configs.flask import FLASK_APP_HOST, FLASK_APP_PORT, FLASK_DEBUG_MODE
from configs.web3 import ENDPOINT, ABI_FILEPATH


thread_lock = threading.Lock()
logger = logging.getLogger(__name__)

init_tm_logger()

app = Flask(__name__)
app.port = FLASK_APP_PORT
app.host = FLASK_APP_HOST
app.use_reloader = False

web3 = init_web3(ENDPOINT)
wallet = init_wallet(web3)
skale = Skale(ENDPOINT, ABI_FILEPATH, wallet)
nonce_manager = NonceManager(skale, wallet)


@app.route('/sign-and-send', methods=['POST'])
def _sign_and_send():
    logger.info(request)
    transaction_dict_str = request.json.get('transaction_dict')
    transaction_dict = json.loads(transaction_dict_str)
    thread_id = threading.get_ident()
    logger.info(f'thread_id {thread_id} waiting for the lock')
    with thread_lock:
        logger.info(f'thread_id {thread_id} got the lock')
        tx_hash, error = sign_and_send(transaction_dict, wallet, nonce_manager)
        if error is None:
            logger.warning(f'thread_id {thread_id} going to release the lock')
            return construct_ok_response({'transaction_hash': tx_hash})
        else:
            logger.warning(f'thread_id {thread_id} going to release the lock due to an error')
            return construct_err_response(HTTPStatus.BAD_REQUEST, error)


@app.route('/sign', methods=['POST'])
def _sign():
    logger.info(request)
    transaction_dict_str = request.json.get('transaction_dict')
    transaction_dict = json.loads(transaction_dict_str)
    signed_transaction = None
    with thread_lock:
        try:
            signed_transaction = wallet.sign(transaction_dict)
        except Exception as e:  # todo: catch specific error
            logger.error(e)
            return construct_err_response(HTTPStatus.BAD_REQUEST, e)

    logger.info(f'Transaction signed - {signed_transaction}')
    return construct_ok_response({
        'rawTransaction': signed_transaction.rawTransaction.hex(),
        'hash': signed_transaction.hash.hex(),
        'r': signed_transaction.r,
        's': signed_transaction.s,
        'v': signed_transaction.v
    })


@app.route('/sign-hash', methods=['POST'])
def _sign_hash():
    logger.info(request)
    unsigned_hash = request.json.get('unsigned_hash')
    signed_data = None
    with thread_lock:
        try:
            signed_data = wallet.sign_hash(unsigned_hash)
        except Exception as e:  # todo: catch specific error
            logger.error(e)
            return construct_err_response(HTTPStatus.BAD_REQUEST, e)

    logger.info(f'Hash signed - signed data: {signed_data}')

    data = {
        'messageHash': signed_data.messageHash.hex(),
        'r': signed_data.r,
        's': signed_data.s,
        'v': signed_data.v,
        'signature': signed_data.signature.hex()
    }
    return construct_ok_response(data)


@app.route('/address', methods=['GET'])
def _address():
    logger.info(request)
    return construct_ok_response({'address': wallet.address})


@app.route('/public-key', methods=['GET'])
def _public_key():
    logger.info(request)
    return construct_ok_response({'public_key': wallet.public_key})


def main():
    logger.info(arguments_list_string({
        'Ethereum RPC endpoint': ENDPOINT}, 'Starting Transaction Manager'))
    app.run(debug=FLASK_DEBUG_MODE, port=FLASK_APP_PORT,
            host=FLASK_APP_HOST, use_reloader=False)


if __name__ == '__main__':
    main()
