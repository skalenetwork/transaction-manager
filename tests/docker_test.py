import json
from concurrent.futures import as_completed, ThreadPoolExecutor

import pytest
from skale.wallets import RedisWallet

TX_NUMBER = 15


@pytest.fixture
def rwallet(trs, w3wallet):
    """ Redis wallet for docker based tests """
    return RedisWallet(trs, 'transactions', w3wallet)


def make_simple_tx(rwallet, address):
    etx = {'to': address, 'value': 10}
    return rwallet.sign_and_send(etx)


def wait_for_tx(rwallet, tx_id):
    rwallet.wait(tx_id, timeout=300)
    return rwallet.get_record(tx_id)


@pytest.mark.skip
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
    rec = rwallet.wait(tx_id, timeout=60)
    assert rec['status'] == 1
    tx = rwallet.get_record(tx_id)
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


def test_processor_many_tx(tpool, eth, w3, trs, rwallet):
    addrs = [w3.eth.account.create().address for i in range(TX_NUMBER)]
    futures = []
    with ThreadPoolExecutor(max_workers=3) as p:
        futures = [p.submit(make_simple_tx, rwallet, addr) for addr in addrs]

    tids = [f.result() for f in as_completed(futures)]

    with ThreadPoolExecutor(max_workers=3) as p:
        futures = [p.submit(wait_for_tx, rwallet, tid) for tid in tids]
    txs = [f.result() for f in as_completed(futures)]
    assert any(tx['status'] == 'SUCCESS' for tx in txs)
