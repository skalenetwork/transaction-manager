import time

from transaction_manager.transaction import TxStatus


def test_get_next_rdp(tpool, rdp):
    eth_tx_a = {
        'to': '0xa',
        'value': 10,
        'gasPrice': 1,
        'gas': 22000,
        'nonce': 0
    }
    aid = rdp.sign_and_send(eth_tx_a, priority=2)
    time.sleep(1)
    assert tpool.size == 1
    next_tx = tpool.fetch_next()

    assert next_tx.tx_id == aid
    assert next_tx is not None
    assert next_tx.to == eth_tx_a['to']
    assert next_tx.value == eth_tx_a['value']
    assert next_tx.gas_price == eth_tx_a['gasPrice']
    assert next_tx.gas == eth_tx_a['gas']
    assert next_tx.priority == 2
    assert next_tx.nonce == 0
    assert next_tx.hashes == []
    assert next_tx.tx_hash is None
    assert next_tx.tx_id.startswith('tx')
    assert len(next_tx.tx_id) == 35

    eth_tx_b = {'to': '0xb', 'value': 10}
    eth_tx_c = {'to': '0xc', 'value': 10}
    eth_tx_d = {'to': '0xd', 'value': 10}
    bid = rdp.sign_and_send(eth_tx_b, priority=2)
    time.sleep(1)
    cid = rdp.sign_and_send(eth_tx_c, priority=2)
    time.sleep(1)
    did = rdp.sign_and_send(eth_tx_d, priority=2)
    time.sleep(1)

    print(aid)
    print(bid)
    print(cid)
    print(did)

    for i in range(5):
        # TODO: FIX !!
        assert tpool.get_next_id() == did.encode('utf-8')

    eth_tx_e = {'to': '0xe', 'value': 10}
    eid = rdp.sign_and_send(eth_tx_e, priority=3)
    for i in range(5):
        assert tpool.get_next_id() == eid.encode('utf-8')


def test_get_next(tpool, trs):
    assert tpool.size == 0
    assert tpool.get_next_id() is None
    assert tpool.fetch_next() is None

    valid_record = b'{"attempts": 0, "chain_id": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "nonce": 3, "priority": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "value": 1}'  # noqa
    transactions = [
        (b'tx-1', 3, b''),
        (b'tx-2', 2, b'{}'),
        (b'tx-3', 1, valid_record),
    ]
    for t in transactions:
        tpool._add_record(*t)

    tx = tpool.fetch_next()
    assert tx.tx_id == 'tx-3'
    assert tpool.size == 1

    tx.status = TxStatus.TIMEOUT
    tpool.save(tx)
    tx = tpool.fetch_next()
    assert tx.status == TxStatus.TIMEOUT

    tpool.release(tx)
    assert tpool.size == 0
