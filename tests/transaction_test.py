from transaction_manager.transaction import Tx, TxStatus

# TODO: add converting from eth tx test


def test_tx():
    tx = Tx(
        tx_id='1232321332132131331321',
        status=TxStatus.PROPOSED,
        priority=1,
        to='0x1',
        value=1,
        gas_price=1000000000,
        gas=22000,
        nonce=3,
        source=None,
        tx_hash=None,
        data={'test': 1}
    )

    assert tx.eth_tx == {
        'from': None,
        'to': '0x1',
        'value': 1,
        'gasPrice': 1000000000,
        'gas': 22000,
        'nonce': 3,
        'chainId': None,
        'data': {'test': 1}
    }
    assert tx.raw_id == b'1232321332132131331321'
    assert not tx.is_sent()

    dumped_tx = tx.to_bytes()
    expected = b'{"attempts": 0, "chain_id": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "nonce": 3, "priority": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "value": 1}'  # noqa
    assert dumped_tx == expected

    loaded_tx = Tx.from_bytes(tx.tx_id.encode('utf-8'), dumped_tx)
    assert loaded_tx == tx

    tx.gas_price = None
    dumped_tx = tx.to_bytes()
    loaded_tx = Tx.from_bytes(tx.tx_id.encode('utf-8'), dumped_tx)
    assert loaded_tx == tx

    tx.gas = None
    dumped_tx = tx.to_bytes()
    loaded_tx = Tx.from_bytes(tx.tx_id.encode('utf-8'), dumped_tx)
    assert loaded_tx == tx

    tx.tx_hash = '0x12323123213213213'
    dumped_tx = tx.to_bytes()
    loaded_tx = Tx.from_bytes(tx.tx_id.encode('utf-8'), dumped_tx)
    assert loaded_tx == tx


def test_tx_completed():
    tx = Tx(
        tx_id='1232321332132131331321',
        status=TxStatus.PROPOSED,
        priority=1,
        to='0x1',
        value=1,
        gas_price=1000000000,
        gas=22000,
        nonce=3,
        data=None,
        tx_hash=None
    )
    assert not tx.is_completed()
    tx.status = TxStatus.PENDING
    assert not tx.is_completed()
    tx.status = TxStatus.TIMEOUT
    assert not tx.is_completed()
    tx.status = TxStatus.NOT_SENT
    assert tx.is_completed()
    tx.status = TxStatus.SUCCESS
    assert tx.is_completed()
    tx.status = TxStatus.FAILED
    assert tx.is_completed()

    tx.status = TxStatus.PENDING
    tx.set_as_completed({'status': 1})
    tx.status == TxStatus.SUCCESS
    tx.set_as_completed({'status': 0})
    tx.status == TxStatus.FAILED
