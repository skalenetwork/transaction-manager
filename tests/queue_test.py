import json
import time
from multiprocessing import Process
from concurrent.futures import as_completed, ThreadPoolExecutor

import pytest
import redis as redis_py
from skale import Skale
from skale.utils.web3_utils import init_web3

from configs import TEST_ABI_FILEPATH
from configs.web3 import ENDPOINT
from tools.helper import init_wallet
from tx_queue import main as run_tx_manager


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


def run_simple_tx(redis, address, amount, gas_price, channel_name):
    message_data = {
        'channel': channel_name,
        'tx': {
            'to': address,
            'value': amount,
            'gasPrice': gas_price,
            'gas': 22000
        }
    }
    redis.publish(f'tx.post.{channel_name}',
                  json.dumps(message_data).encode('utf-8'))


def test_send_tx(tx_manager, redis, skale):
    amount_to_send = 5
    channel_name = 'schain.test'
    sub = redis.pubsub()
    sub.subscribe(f'tx.receipt.{channel_name}')
    run_simple_tx(redis, skale.wallet.address, amount_to_send,
                  skale.web3.eth.gasPrice, channel_name)
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
    channel_name = 'schain.test'
    sub = redis.pubsub()
    sub.subscribe(f'tx.receipt.{channel_name}')
    run_simple_tx(redis, skale.wallet.address, amount_to_send,
                  skale.web3.eth.gasPrice, channel_name)
    time.sleep(5)
    message = sub.get_message()
    assert message['type'] == 'subscribe'
    message = sub.get_message()
    assert message['type'] == 'message'
    msg_data = json.loads(message['data'].decode('utf-8'))
    assert msg_data['channel'] == channel_name
    assert msg_data['status'] == 'error'
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


def test_send_txs_concurrently(tx_manager, redis, skale):
    # TODO: Implement
    max_workers = 10
    tx_number = 10
    amount_to_send = 5
    channel_name_template = 'schain{}.test'
    channels = [channel_name_template.format(i) for i in range(tx_number)]
    subs = []
    for channel in channels:
        sub = redis.pubsub()
        sub.subscribe(f'tx.receipt.{channel}')
        subs.append(sub)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                run_simple_tx,
                redis, skale.wallet.address, amount_to_send,
                skale.web3.eth.gasPrice, channel
            )
            for channel in channels
        ]
        for future in as_completed(futures):
            future.result()

    def check_message(sub, channel_name):
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

    for sub, channel_name in zip(subs, channels):
        check_message(sub, channel_name)
