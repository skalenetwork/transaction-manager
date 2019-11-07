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

from flask import Flask, request
from skale import Skale
from skale.utils.helper import init_default_logger

from nonce_manager import NonceManager
from core import sign_and_send, wait_for_the_next_block

from utils.str_formatters import arguments_list_string
from utils.helper import construct_ok_response, get_software_wallet

from configs.flask import FLASK_APP_HOST, FLASK_APP_PORT, FLASK_DEBUG_MODE, FLASK_SECRET_KEY
from configs.web3 import ENDPOINT, ABI_FILEPATH


init_default_logger()

logger = logging.getLogger(__name__)
app = Flask(__name__)
skale = Skale(ENDPOINT, ABI_FILEPATH)
wallet = get_software_wallet()
nonce_manager = NonceManager(skale, wallet)


@app.route('/sign-and-send', methods=['POST'])
def post_sign_and_send():
    logger.debug(request)
    transaction_dict_str = request.json.get('transaction_dict')
    transaction_dict = json.loads(transaction_dict_str)
    tx = sign_and_send(skale.web3, nonce_manager, transaction_dict, wallet)
    return construct_ok_response({'tx': skale.web3.toHex(tx)})


if __name__ == '__main__':
    logger.info(arguments_list_string({'Ehereum RPC endpoint': ENDPOINT}, 'Starting Flask server'))
    app.secret_key = FLASK_SECRET_KEY
    wait_for_the_next_block(skale)
    nonce_manager.request_network_nonce()
    app.run(debug=FLASK_DEBUG_MODE, port=FLASK_APP_PORT, host=FLASK_APP_HOST, use_reloader=False)
