import json
import mock
import copy
from random import randint

import pytest


from custom_thread import CustomThread
from utils import get_bp_data, post_bp_data
from tools.helper import crop_tx_dict
from main import app, wallet


TX_DICT = {
    'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
    'value': 9,
    'gas': 210000,
    'gasPrice': 1000000,
    'data': '0x0'
}


@pytest.fixture
def skale_bp():
    yield app.test_client()


def test_crop_tx_dict():
    tx_dict = copy.deepcopy(TX_DICT)
    tx_dict['data'] = '0x' + '0' * 1000
    cropped = crop_tx_dict(tx_dict)
    assert tx_dict['data'] == '0x' + '0' * 1000
    assert cropped['data'] == '0x' + '0' * 48
    cropped.pop('data')
    tx_dict.pop('data')
    assert cropped == tx_dict


def test_crop_tx_dict_without_data():
    tx_dict = copy.deepcopy(TX_DICT)
    tx_dict.pop('data')
    cropped = crop_tx_dict(tx_dict)
    assert cropped == tx_dict


def test_index(skale_bp):
    data = get_bp_data(skale_bp, '/')
    assert data == {'data': {'status': 'ok'}, 'error': None}


def test_sign_and_send(web3, skale_bp):
    tx_dict_str = json.dumps(TX_DICT)
    response = post_bp_data(skale_bp, '/sign-and-send', params={
        'transaction_dict': tx_dict_str
    })
    assert response['error'] is None
    data = response['data']
    tx_hash = data.get('transaction_hash')
    assert isinstance(tx_hash, str)
    receipt = web3.eth.getTransactionReceipt(tx_hash)
    assert receipt is not None
    assert receipt['status'] == 1


# @mock.patch('main.sign_and_send', side_effect=Exception)
def test_sign_and_send_500_error(web3, skale_bp):
    tx_dict_str = json.dumps({})
    response = post_bp_data(skale_bp, '/sign-and-send', params=tx_dict_str,
                            plain_response=True)
    assert response.status_code == 500
    assert response.data == b'{"data": null, "error": null}'


@mock.patch('main.sign_and_send',
            return_value=(None, 'Failed to fetch receipt'))
def test_sign_and_send_error_not_none(web3, skale_bp):
    tx_dict_str = json.dumps(TX_DICT)
    response = post_bp_data(skale_bp, '/sign-and-send', params={
        'transaction_dict': tx_dict_str
    }, plain_response=True)
    assert response.status_code == 400
    assert response.data == \
        b'{"data": null, "error": "Failed to fetch receipt"}'


def send_transactions(opts):
    for _ in range(0, 10):
        amount = randint(0, 100000)
        txn = {
            'to': opts['wallet'].address,
            'value': amount,
            'gasPrice': opts['wallet']._web3.eth.gasPrice,
            'gas': 22000
        }
        tx_dict_str = json.dumps(txn)
        result = post_bp_data(opts['skale_bp'], '/sign-and-send', params={
            'transaction_dict': tx_dict_str
        })
        data = result['data']
        assert isinstance(data['transaction_hash'], str)


def test_multithreading(skale_bp):
    threads = []
    N_THREADS = 5
    for i in range(0, N_THREADS):
        thread = CustomThread(
            f'Thread i={i}', send_transactions,
            opts={
                'skale_bp': skale_bp,
                'wallet': wallet
            },
            once=True
        )
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
        assert not thread.err
