import json
from multiprocessing import Process

import pytest

from transaction_manager.processor import Processor


@pytest.fixture
def proc(tpool, eth, w3wallet, trs):
    p = Processor(eth, tpool, w3wallet)
    r = Process(target=p.run)
    r.start()
    yield p
    r.terminate()


def test_processor(proc, tpool, eth, w3wallet, trs, sender):
    eth_tx_a = {
        'from': w3wallet.address,
        'to': w3wallet.address,
        'value': 10,
        'gasPrice': 1,
        'gas': 22000,
        'nonce': 0
    }
    tx_id = sender.send(eth_tx_a)
    tx = sender.wait(tx_id, timeout=300)
    assert tx['status'] == 'SUCCESS'
    assert tx['from'] == w3wallet.address
    assert tx['to'] == w3wallet.address
    assert tx['nonce'] == eth.get_nonce(w3wallet.address) - 1
    last_attempt = json.loads(trs.get(b'last_attempt').decode('utf-8'))
    assert tx['nonce'] == last_attempt['nonce']
    assert tx['attempts'] == last_attempt['index']
    assert tx['gasPrice'] == last_attempt['gas_price']
    assert tx['data'] is None
    assert tx['priority'] == 1
    assert tx_id == last_attempt['tx_id']
