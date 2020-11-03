import json
import copy
from random import randint

import pytest

from main import app, skale
from hexbytes import HexBytes
from eth_account._utils import transactions

from custom_thread import CustomThread
from tests.utils import get_bp_data, post_bp_data
from tools.helper import crop_tx_dict


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


def test_address(skale_bp):
    response = get_bp_data(skale_bp, '/address')
    assert response['error'] is None
    assert response['data']['address'] == skale.wallet.address


def test_public_key(skale_bp):
    response = get_bp_data(skale_bp, '/public-key')
    assert response['error'] is None
    assert response['data']['public_key'] == skale.wallet.public_key


def test_sign(skale_bp):
    tx_dict_str = json.dumps(TX_DICT)
    response = post_bp_data(skale_bp, '/sign', params={
        'transaction_dict': tx_dict_str
    })

    signed_transaction = skale.wallet.sign(TX_DICT)

    assert response['error'] is None
    data = response['data']
    assert data['rawTransaction'] == signed_transaction.rawTransaction.hex()
    assert data['hash'] == signed_transaction.hash.hex()
    assert data['r'] == signed_transaction.r
    assert data['s'] == signed_transaction.s
    assert data['v'] == signed_transaction.v


def test_sign_and_send(skale_bp):
    tx_dict_str = json.dumps(TX_DICT)
    response = post_bp_data(skale_bp, '/sign-and-send', params={
        'transaction_dict': tx_dict_str
    })
    assert response['error'] is None
    data = response['data']
    assert isinstance(data['transaction_hash'], str), data


def test_send_transaction_errored(skale_bp):
    txn = {}
    tx_dict_str = json.dumps(txn)
    response = post_bp_data(skale_bp, '/sign-and-send', params={
        'transaction_dict': tx_dict_str
    })
    assert response['data'] is None
    assert response['error'] in (
        "Transaction must include these fields: {'gas', 'gasPrice'}",
        "Transaction must include these fields: {'gasPrice', 'gas'}"
    )


def test_sign_hash(skale_bp):
    unsigned_transaction = transactions.serializable_unsigned_transaction_from_dict(TX_DICT)
    raw_hash = unsigned_transaction.hash()
    unsigned_hash = HexBytes(raw_hash).hex()
    response = post_bp_data(skale_bp, '/sign-hash', params={
        'unsigned_hash': unsigned_hash
    })

    assert response['error'] is None
    signed_hash = skale.wallet.sign_hash(unsigned_hash)

    data = response['data']
    assert data['signature'] == signed_hash.signature.hex()
    assert data['messageHash'] == signed_hash.messageHash.hex()
    assert data['r'] == signed_hash.r
    assert data['s'] == signed_hash.s
    assert data['v'] == signed_hash.v


def send_transactions(opts):
    for _ in range(0, 10):
        amount = randint(0, 100000)
        txn = {
            'to': opts['skale'].wallet.address,
            'value': amount,
            'gasPrice': opts['skale'].web3.eth.gasPrice,
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
                'skale': skale
            },
            once=True
        )
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
        assert not thread.err
