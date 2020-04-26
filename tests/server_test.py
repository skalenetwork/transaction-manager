import json
import pytest
from server import app

EMPTY_HEX_STR = '0x0'

TX_DICT = {
    'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
    'value': 9,
    'gas': 200000,
    'gasPrice': 1,
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
def skale_bp(skale):
    yield app.test_client()


def test_address(skale_bp, skale):
    data = get_bp_data(skale_bp, '/address')
    assert data['address'] == skale.wallet.address


def test_public_key(skale_bp, skale):
    data = get_bp_data(skale_bp, '/public-key')
    assert data['public_key'] == skale.wallet.public_key


def test_sign(skale_bp):
    tx_dict_str = json.dumps(TX_DICT)
    data = post_bp_data(skale_bp, '/sign', params={
        'transaction_dict': tx_dict_str
    })
    assert data == {
        'rawTransaction': '0xf860070183030d40941057dc7277a319927d3eb43e05680b75a00eb5f409001ca0276879f94c629092cec95ed21d0a5bd82c96bc35c34e2ede4136a36feb068117a07cda82e439d2067fb494fad5c310ae4c01b2ba9039990864cba917e0934f6422', # noqa
        'hash': '0xd18ef6658f239dd9418bc715b3cc0485f82dec61606984c720d3fd8789306798',
        'r': 17824795021863304244634228817752924303987434134354814486894395563431992656151,
        's': 56472869264428842883394759918096303684550174095081340508173620982012638618658,
        'v': 28
    }


def test_sign_and_send(skale_bp):
    tx_dict_str = json.dumps(TX_DICT)
    data = post_bp_data(skale_bp, '/sign-and-send', params={
        'transaction_dict': tx_dict_str
    })
    assert isinstance(data['transaction_hash'], str)

# todo: add tests for multiple concurrent transactions
