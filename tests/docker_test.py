import json
from concurrent.futures import as_completed, ThreadPoolExecutor

import pytest
from skale.wallets import RedisWalletAdapter

TX_NUMBER = 100


@pytest.fixture
def rdp(trs, w3wallet):
    """ Redis wallet for docker based tests """
    return RedisWalletAdapter(trs, 'transactions', w3wallet)


def make_simple_tx(rdp, address):
    etx = {'to': address, 'value': 10}
    return rdp.sign_and_send(etx)


def wait_for_tx(rdp, tx_id):
    rdp.wait(tx_id, timeout=300)
    return rdp.get_record(tx_id)


def test_processor(tpool, eth, trs, w3wallet, rdp):
    eth_tx_a = {
        'from': rdp.address,
        'to': rdp.address,
        'value': 10,
        'gasPrice': 1,
        'gas': 22000,
        'nonce': 0
    }
    tx_id = rdp.sign_and_send(eth_tx_a)
    rec = rdp.wait(tx_id, timeout=60)
    assert rec['status'] == 1
    tx = rdp.get_record(tx_id)
    assert tx['status'] == 'SUCCESS'
    assert tx['from'] == rdp.address
    assert tx['to'] == rdp.address
    assert tx['nonce'] == eth.get_nonce(rdp.address) - 1
    last_attempt = json.loads(trs.get(b'last_attempt').decode('utf-8'))
    assert tx['nonce'] == last_attempt['nonce']
    assert tx['attempts'] == last_attempt['index']
    assert tx['gasPrice'] == last_attempt['gas_price']
    assert tx['data'] is None
    assert tx['score'] == 1
    assert tx_id == last_attempt['tx_id']


def test_processor_many_tx(tpool, eth, w3, trs, rdp):
    addrs = [w3.eth.account.create().address for i in range(TX_NUMBER)]
    futures = []
    with ThreadPoolExecutor(max_workers=3) as p:
        futures = [p.submit(make_simple_tx, rdp, addr) for addr in addrs]

    tids = [f.result() for f in as_completed(futures)]

    with ThreadPoolExecutor(max_workers=3) as p:
        futures = [p.submit(wait_for_tx, rdp, tid) for tid in tids]
    txs = [f.result() for f in as_completed(futures)]
    assert any(tx['status'] == 'SUCCESS' for tx in txs)
    assert tpool.size == 0
