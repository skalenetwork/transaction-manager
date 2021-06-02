import pytest

from transaction_manager.transaction import TxStatus
from transaction_manager.txpool import NoNextTransactionError

# TODO: Add test for tx with data


def test_get_next(tpool, trs, rdp):
    assert tpool.size == 0
    assert tpool.get_next() is None

    eth_tx_a = {
        'to': '0xa',
        'value': 10,
        'gasPrice': 1,
        'gas': 22000,
        'nonce': 0
    }
    aid = rdp.sign_and_send(eth_tx_a, priority=2)
    next_tx = tpool.get_next()

    assert next_tx.tx_id == aid
    assert next_tx is not None
    assert next_tx.to == eth_tx_a['to']
    assert next_tx.value == eth_tx_a['value']
    assert next_tx.gas_price == eth_tx_a['gasPrice']
    assert next_tx.gas == eth_tx_a['gas']
    assert next_tx.priority == 2
    assert next_tx.nonce == 0
    assert next_tx.receipt is None
    assert next_tx.tx_hash is None
    assert next_tx.tx_id.startswith('tx')
    assert len(next_tx.tx_id) == 35

    eth_tx_b = {'to': '0xb', 'value': 10}
    bid = rdp.send(eth_tx_b, priority=3)
    next_tx = tpool.get_next()
    assert next_tx.tx_id == bid


def test_mark_get_last(tpool, trs, rdp):
    assert tpool.get_last() is None
    eth_tx_a = {'to': '0xa', 'value': 10}
    aid = rdp.send(eth_tx_a, priority=2)
    assert tpool.get_last() is None

    tpool.set_last_id(aid)
    assert tpool.get_last().tx_id == aid

    eth_tx_b = {'to': '0xb', 'value': 10}
    bid = rdp.send(eth_tx_b, priority=2)
    assert tpool.get_last().tx_id == aid

    tpool.set_last_id(bid)
    assert tpool.get_last().tx_id == bid


def test_aquire_release_no_tx():
    pass


def test_aquire_release(tpool, rdp):
    with pytest.raises(NoNextTransactionError):
        with tpool.aquire_next():
            pass

    eth_tx_a = {'to': '0xa', 'value': 10}
    aid = rdp.send(eth_tx_a, priority=2)
    eth_tx_b = {'to': '0xb', 'value': 10}
    bid = rdp.send(eth_tx_b, priority=1)

    with tpool.aquire_next() as atx:
        assert atx.tx_id == aid
        atx.status = TxStatus.SUCCESS

    assert tpool.size == 1
    assert tpool.get(aid.encode('utf-8')).status == TxStatus.SUCCESS

    with tpool.aquire_next() as btx:
        assert btx.tx_id == bid
        btx.status = TxStatus.SENT

    assert tpool.size == 1
    assert tpool.get(bid.encode('utf-8')).status == TxStatus.SENT
