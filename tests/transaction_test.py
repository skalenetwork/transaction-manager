from transaction_manager.structures import Tx, TxStatus

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
        data=None,
        tx_hash=None,
        receipt=None
    )

    assert tx.eth_tx == {
        'to': '0x1',
        'value': 1,
        'gasPrice': 1000000000,
        'gas': 22000,
        'nonce': 3,
        'data': None
    }

    dumped_tx = tx.to_bytes()
    assert dumped_tx == b'{"status": "PROPOSED", "priority": 1, "to": "0x1", "value": 1, "gas": 22000, "nonce": 3, "data": null, "tx_hash": null, "receipt": null, "gasPrice": 1000000000}'  # noqa

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


def test_tx_is_completed():
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
        tx_hash=None,
        receipt=None
    )
    assert not tx.is_completed()
    tx.status = TxStatus.PENDING
    assert not tx.is_completed()
    tx.status = TxStatus.FAILED
    assert tx.is_completed()
    tx.status = TxStatus.TIMEOUT
    assert tx.is_completed()
    tx.status = TxStatus.SUCCESS
    assert tx.is_completed()
