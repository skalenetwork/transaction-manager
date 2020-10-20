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

import enum
import json
import logging

from redis import Redis
from eth_account.datastructures import AttributeDict
from hexbytes import HexBytes
from skale.utils.web3_utils import init_web3, wait_for_receipt_by_blocks
from skale.wallets import BaseWallet
from web3 import Web3

from configs import ENDPOINT, REDIS_URI
from tools.logger import init_tm_logger
from tools.wallet import init_wallet

init_tm_logger()
logger = logging.getLogger(__name__)

POST_CHANNEL_PATTERN = 'tx.post.*'
RECEIPT_CHANNEL_TEMPLATE = 'tx.receipt.{}'


class ErrorType(enum.Enum):
    NOT_SENT = 'not-sent'
    NOT_FOUND = 'not-found'
    TX_FAILED = 'tx-failed'


def send_response(redis: Redis, channel: str,
                  status: str, payload: dict) -> None:
    data = {
        'channel': channel,
        'status': status,
        'payload': payload,
    }
    raw_data = json.dumps(data).encode('utf-8')
    channel = RECEIPT_CHANNEL_TEMPLATE.format(channel)
    logger.info(f'Sending response with status {status} into {channel} channel')
    redis.publish(channel, raw_data)


def make_error_payload(error_type: str, tx_hash: str, err: Exception,
                       receipt: dict) -> dict:
    msg = None if err is None else str(err)
    return {
        'type': error_type,
        'tx_hash': None,
        'msg': msg,
        'receipt': None
    }


def attribute_dict_to_dict(at_dict: AttributeDict) -> dict:
    plain_data = {}
    for key, value in at_dict.items():
        if isinstance(value, HexBytes):
            plain_data[key] = value.hex()
        else:
            plain_data[key] = value
    return plain_data


def channel_tx_from_message(message: dict) -> tuple:
    data = message.get('data')
    data = json.loads(data.decode('utf-8'))
    channel = data.get('channel')
    tx = data.get('tx')
    return channel, tx


def handle_tx_message(redis: Redis, web3: Web3, wallet: BaseWallet,
                      message: dict) -> dict:
    channel, tx = channel_tx_from_message(message)
    if channel is None or tx is None:
        logger.warning(f'Invalid tx message data: {channel} - {tx}')
        return
    method = tx.get('method')
    logger.info(f'Trying to sent transaction in {channel} with method {method}')
    tx['nonce'] = web3.eth.getTransactionCount(wallet.address)
    try:
        tx_hash = wallet.sign_and_send(tx)
    except Exception as err:
        logger.exception(f'Sending tx in channel {channel} failed')
        payload = make_error_payload('not-sent', None, err, None)
        send_response(redis, channel, status='error', payload=payload)
        return
    logger.info(f'Waiting for transaction receipt for '
                f'hash: {tx_hash} and channel {channel}')
    try:
        attr_dict_receipt = wait_for_receipt_by_blocks(web3, tx_hash)
    except Exception as err:
        logger.exception(f'Waiting for receipt failed for channel {channel}')
        payload = make_error_payload('not-found', tx_hash, err, None)
        send_response(redis, channel, status='error', payload=payload)
        return
    logger.info(f'Received transaction receipt for channel {channel}')
    receipt = attribute_dict_to_dict(attr_dict_receipt)
    if receipt['status'] != 1:
        logger.exception(f'Transaction failed for channel {channel}')
        payload = make_error_payload('tx-failed', tx_hash, None, receipt)
        send_response(redis, channel, status='error', payload=payload)
        return
    send_response(redis, channel, status='ok', payload={'receipt': receipt})


def main() -> None:
    logger.info('Starting transaction manager ...')
    redis = Redis.from_url(REDIS_URI, db=0)
    sub = redis.pubsub()
    sub.psubscribe(POST_CHANNEL_PATTERN)
    web3 = init_web3(ENDPOINT)
    wallet = init_wallet(web3)
    for message in sub.listen():
        msg_type = message.get('type')
        if msg_type == 'pmessage':
            handle_tx_message(redis, web3, wallet, message)


if __name__ == '__main__':
    main()
