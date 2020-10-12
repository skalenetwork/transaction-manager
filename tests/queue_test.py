import json
import os
import time
from multiprocessing import Process

import pytest
import redis as redis_py
from skale import Skale
from skale.utils.web3_utils import init_web3

from configs.web3 import ENDPOINT
from tools.helper import init_wallet
from tx_queue import main as run_tx_manager

TEST_ABI_FILEPATH = os.getenv('TEST_ABI_FILEPATH')


@pytest.fixture
def tx_manager():
    p = Process(target=run_tx_manager)
    p.start()
    yield
    p.terminate()


@pytest.fixture
def redis():
    return redis_py.Redis(host='localhost', port=6379, db=0)


@pytest.fixture
def skale():
    web3 = init_web3(ENDPOINT)
    wallet = init_wallet(web3)
    return Skale(ENDPOINT, TEST_ABI_FILEPATH, wallet)


@pytest.mark.skip
def test_run_tx_manager():
    run_tx_manager()


def test_send_tx(tx_manager, redis, skale):
    amount_to_send = 5
    txn = {
        'to': skale.wallet.address,
        'value': amount_to_send,
        'gasPrice': skale.web3.eth.gasPrice,
        'gas': 22000
    }
    schain_name = 'test'
    channel_name = f'schain.{schain_name}'
    message_data = {
        'channel': channel_name,
        'tx': txn
    }
    sub = redis.pubsub()
    sub.subscribe(f'tx.receipt.{channel_name}')
    redis.publish(f'tx.post.{channel_name}',
                  json.dumps(message_data).encode('utf-8'))
    time.sleep(5)
    message = sub.get_message()
    assert message['type'] == 'subscribe'
    message = sub.get_message()
    assert message['type'] == 'message'
    msg_data = json.loads(message['data'].decode('utf-8'))
    assert msg_data['channel'] == channel_name
    receipt = msg_data['payload']['receipt']
    assert receipt['status'] == 1
    assert receipt['to'] == skale.wallet.address
    assert msg_data['status'] == 'ok'
    # TODO: Check from address


def test_send_tx_failed(tx_manager, redis, skale):
    amount_to_send = -1  # invalid amount
    txn = {
        'to': skale.wallet.address,
        'value': amount_to_send,
        'gasPrice': skale.web3.eth.gasPrice,
        'gas': 22000
    }

    schain_name = 'test'
    channel_name = f'schain.{schain_name}'
    message_data = {
        'channel': channel_name,
        'tx': txn
    }
    sub = redis.pubsub()
    sub.subscribe(f'tx.receipt.{channel_name}')
    redis.publish(f'tx.post.{channel_name}',
                  json.dumps(message_data).encode('utf-8'))
    time.sleep(5)
    message = sub.get_message()
    assert message['type'] == 'subscribe'
    message = sub.get_message()
    assert message['type'] == 'message'
    msg_data = json.loads(message['data'].decode('utf-8'))
    assert msg_data['channel'] == channel_name
    assert msg_data['status'] == 'error'
    print(repr(msg_data))
    # TODO: Investigate, may be ganache specific
    assert msg_data == {
        'channel': 'schain.test',
        'status': 'error',
        'payload': {
            'type': 'not-sent',
            'tx_hash': None,
            'msg': 'Serialization failed because of field value ("Cannot serialize negative integers")',  # noqa
            'receipt': None
        }
    }
    # TODO: Add other error types coverage


def test_send_txs_concurrently():
    # TODO: Implement
    pass
