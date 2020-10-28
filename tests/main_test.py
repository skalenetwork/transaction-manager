import json
import os
import time
from concurrent.futures import as_completed, ThreadPoolExecutor
from multiprocessing import Process

import pytest
import redis as redis_py
from sgx import SgxClient
from skale import Skale
from skale.utils.account_tools import send_ether
from skale.utils.web3_utils import init_web3
from skale.wallets import Web3Wallet

from configs import ENDPOINT, NODE_CONFIG_FILEPATH
from configs.sgx import SGX_SERVER_URL, SGX_CERTIFICATES_FOLDER
from tools.wallet import init_sgx_wallet
from main import main as run_tx_manager

TEST_ABI_FILEPATH = os.getenv('TEST_ABI_FILEPATH')
ETH_PRIVATE_KEY = os.getenv('ETH_PRIVATE_KEY')


@pytest.fixture
def sgx_key():
    if not os.path.isdir(SGX_CERTIFICATES_FOLDER):
        # Useful debug info. Will be removed in cleanup script
        os.mkdir(SGX_CERTIFICATES_FOLDER)
    sgx = SgxClient(SGX_SERVER_URL, SGX_CERTIFICATES_FOLDER)
    key_info = sgx.generate_key()
    with open(NODE_CONFIG_FILEPATH, 'w') as node_config_file:
        json.dump({'sgx_key_name': key_info.name}, node_config_file)
    yield key_info.name


@pytest.fixture
def tx_manager(sgx_key):
    try:
        from pytest_cov.embed import cleanup_on_sigterm
    except ImportError:
        pass
    else:
        cleanup_on_sigterm()
    p = Process(target=run_tx_manager)
    p.start()
    # Wait for tm initialization
    yield p
    if p.is_alive():
        p.terminate()


@pytest.fixture
def redis():
    return redis_py.Redis(host='localhost', port=6379, db=0)


@pytest.fixture
def skale():
    web3 = init_web3(ENDPOINT)
    owner_wallet = Web3Wallet(ETH_PRIVATE_KEY, web3)
    wallet = init_sgx_wallet(SGX_SERVER_URL, web3)
    eth_amount = 1000
    send_ether(web3, owner_wallet, wallet.address, eth_amount)
    return Skale(ENDPOINT, TEST_ABI_FILEPATH, wallet)


@pytest.mark.skip
def test_run_tx_manager(tx_manager):
    timeout_to_wait_tm_init = 50
    time.sleep(timeout_to_wait_tm_init)


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


def wait_for_response(sub):
    result_message = None
    for msg in sub.listen():
        msg_type = msg.get('type')
        if msg_type == 'message':
            result_message = msg
            break
    return result_message


def test_send_tx(tx_manager, redis, skale):
    amount_to_send = 5
    channel_name = 'schain.test'
    sub = redis.pubsub()
    sub.subscribe(f'tx.receipt.{channel_name}')
    run_simple_tx(redis, skale.wallet.address, amount_to_send,
                  skale.web3.eth.gasPrice, channel_name)
    message = wait_for_response(sub)
    assert message['type'] == 'message'
    msg_data = json.loads(message['data'].decode('utf-8'))
    assert msg_data['channel'] == channel_name
    tx_hash = msg_data['payload']['receipt']
    assert tx_hash
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
    message = wait_for_response(sub)
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
    # Sleep to mine all the unmined transactions
    time.sleep(50)
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
        message = wait_for_response(sub)
        msg_data = json.loads(message['data'].decode('utf-8'))
        assert msg_data['channel'] == channel_name
        receipt = msg_data['payload']['receipt']
        assert receipt['status'] == 1
        assert receipt['to'] == skale.wallet.address
        assert msg_data['status'] == 'ok'

    for sub, channel_name in zip(subs, channels):
        check_message(sub, channel_name)
