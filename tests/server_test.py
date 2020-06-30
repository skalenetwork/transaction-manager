import json
import pytest
from main import app, skale
from hexbytes import HexBytes
from eth_account._utils import transactions

EMPTY_HEX_STR = '0x0'

TX_DICT = {
    'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
    'value': 9,
    'gas': 200000,
    'gasPrice': 1000000,
    'nonce': 7,
    'chainId': None,
    'data': '0x0'
}


def get_bp_data(bp, request, params=None, full_data=False, **kwargs):
    data = bp.get(request, query_string=params, **kwargs).data
    if full_data:
        return data
    return json.loads(data.decode('utf-8'))['data']


def post_bp_data(bp, request, params=None, full_response=False, **kwargs):
    data = bp.post(request, json=params).data
    if full_response:
        return json.loads(data.decode('utf-8'))
    return json.loads(data.decode('utf-8'))['data']


@pytest.fixture
def skale_bp():
    yield app.test_client()


def test_address(skale_bp):
    data = get_bp_data(skale_bp, '/address')
    assert data['address'] == skale.wallet.address


def test_public_key(skale_bp):
    data = get_bp_data(skale_bp, '/public-key')
    assert data['public_key'] == skale.wallet.public_key


def test_sign(skale_bp):
    tx_dict_str = json.dumps(TX_DICT)
    data = post_bp_data(skale_bp, '/sign', params={
        'transaction_dict': tx_dict_str
    })

    signed_transaction = skale.wallet.sign(TX_DICT)

    assert data['rawTransaction'] == signed_transaction.rawTransaction.hex()
    assert data['hash'] == signed_transaction.hash.hex()
    assert data['r'] == signed_transaction.r
    assert data['s'] == signed_transaction.s
    assert data['v'] == signed_transaction.v


def test_sign_and_send(skale_bp):
    tx_dict_str = json.dumps(TX_DICT)
    data = post_bp_data(skale_bp, '/sign-and-send', params={
        'transaction_dict': tx_dict_str
    })
    assert data
    assert isinstance(data['transaction_hash'], str)


def test_sign_hash(skale_bp):
    unsigned_transaction = transactions.serializable_unsigned_transaction_from_dict(TX_DICT)
    raw_hash = unsigned_transaction.hash()
    unsigned_hash = HexBytes(raw_hash).hex()
    data = post_bp_data(skale_bp, '/sign-hash', params={
        'unsigned_hash': unsigned_hash
    })
    print(data)
    signed_hash = skale.wallet.sign_hash(unsigned_hash)

    assert data['signature'] == signed_hash.signature.hex()
    assert data['messageHash'] == signed_hash.messageHash.hex()
    assert data['r'] == signed_hash.r
    assert data['s'] == signed_hash.s
    assert data['v'] == signed_hash.v

# todo: add tests for multiple concurrent transactions
