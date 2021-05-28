import json
from multiprocessing import Process
from concurrent.futures import as_completed, ProcessPoolExecutor

import pytest

from transaction_manager.processor import Processor

TX_NUMBER = 10


@pytest.fixture
def proc(tpool, eth, w3wallet, trs):
    p = Processor(eth, tpool, w3wallet)
    r = Process(target=p.run)
    r.start()
    yield p
    r.terminate()


def send_tx(sender, etx):
    return sender.send(etx)


def make_simple_tx(sender, address):
    etx = {'to': address, 'value': 10}
    return send_tx(sender, etx)


def wait_for_tx(sender, tx_id):
    return sender.wait(tx_id, timeout=300)


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


def test_processor_many_tx(proc, tpool, eth, w3wallet, w3, trs, sender):
    addrs = [w3.eth.account.create().address for i in range(TX_NUMBER)]
    futures = []
    with ProcessPoolExecutor(max_workers=3) as p:
        futures = [p.submit(make_simple_tx, sender, addr) for addr in addrs]

    tids = [f.result() for f in as_completed(futures)]

    with ProcessPoolExecutor(max_workers=3) as p:
        futures = [p.submit(wait_for_tx, sender, tid) for tid in tids]
    tx = [f.result() for f in as_completed(futures)]
    assert any(tx.status == 'SUCCESS', tx)
