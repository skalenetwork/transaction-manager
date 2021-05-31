import json
import pytest


def test_processor(tpool, eth, trs, w3wallet, rwallet):
    eth_tx_a = {
        'from': rwallet.address,
        'to': rwallet.address,
        'value': 10,
        'gasPrice': 1,
        'gas': 22000,
        'nonce': 0
    }
    tx_id = rwallet.sign_and_send(eth_tx_a)
    tx = rwallet.wait(tx_id, timeout=2)
    assert tx['status'] == 'SUCCESS'
    assert tx['from'] == rwallet.address
    assert tx['to'] == rwallet.address
    assert tx['nonce'] == eth.get_nonce(rwallet.address) - 1
    last_attempt = json.loads(trs.get(b'last_attempt').decode('utf-8'))
    assert tx['nonce'] == last_attempt['nonce']
    assert tx['attempts'] == last_attempt['index']
    assert tx['gasPrice'] == last_attempt['gas_price']
    assert tx['data'] is None
    assert tx['priority'] == 1
    assert tx_id == last_attempt['tx_id']
