import pytest

from transaction_manager.transaction import InvalidFormatError, Tx, TxStatus

# TODO: add converting from eth tx test


def test_tx():
    tx = Tx(
        tx_id='1232321332132131331321',
        status=TxStatus.PROPOSED,
        score=1,
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
    assert tx.hashes == []
    assert tx.raw_id == b'1232321332132131331321'
    assert not tx.is_sent()

    dumped_tx = tx.to_bytes()
    expected = b'{"attempts": 0, "chain_id": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "multiplier": 1.2, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "value": 1}'  # noqa
    print(dumped_tx)
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

    tx.set_as_sent('0x1231231')
    assert tx.hashes == ['0x1231231']

    dumped_tx = tx.to_bytes()
    loaded_tx = Tx.from_bytes(tx.tx_id.encode('utf-8'), dumped_tx)

    assert loaded_tx.tx_hash == '0x1231231'
    assert loaded_tx.hashes == ['0x1231231']

    tx.set_as_sent('0x2231231')
    assert tx.tx_hash == '0x2231231'
    assert tx.hashes == ['0x1231231', '0x2231231']

    assert not tx.is_last_attempt()


def test_tx_statuses():
    tx = Tx(
        tx_id='1232321332132131331321',
        status=TxStatus.PROPOSED,
        score=1,
        to='0x1',
        value=1,
        gas_price=1000000000,
        gas=22000,
        nonce=3,
        data=None,
        tx_hash=None
    )
    assert not tx.is_completed() and not tx.is_mined()
    tx.status = TxStatus.SENT
    assert not tx.is_completed() and not tx.is_mined()
    tx.status = TxStatus.TIMEOUT
    assert not tx.is_completed() and not tx.is_mined()
    tx.status = TxStatus.DROPPED
    assert tx.is_completed() and not tx.is_mined()
    tx.status = TxStatus.SUCCESS
    assert tx.is_completed() and tx.is_mined()
    tx.status = TxStatus.FAILED
    assert tx.is_completed() and tx.is_mined()
    tx.status = TxStatus.MINED
    assert not tx.is_completed() and tx.is_mined()

    tx.status = TxStatus.SENT
    tx.set_as_completed('tx-hash', 1)
    tx.status == TxStatus.SUCCESS
    tx.set_as_completed('tx-hash', 0)
    tx.status == TxStatus.FAILED
    tx.set_as_completed('tx-hash', -1)
    tx.status == TxStatus.FAILED


def test_from_bytes():
    tx_id = b'tx-1232321332132131331321'

    with pytest.raises(InvalidFormatError):
        Tx.from_bytes(tx_id, b'')

    missing_field_status = b'{"attempts": 0, "chain_id": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "nonce": 3, "score": 1, "sent_ts": null, "to": "0x1", "tx_hash": null, "value": 1}'  # noqa

    with pytest.raises(InvalidFormatError):
        Tx.from_bytes(tx_id, missing_field_status)

    missing_field_to = b'{"attempts": 0, "chain_id": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "tx_hash": null, "value": 1}'  # noqa

    with pytest.raises(InvalidFormatError):
        Tx.from_bytes(tx_id, missing_field_to)

    missing_field_hash = b'{"attempts": 0, "chain_id": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "value": 1}'  # noqa
    tx = Tx.from_bytes(tx_id, missing_field_hash)
    assert tx.hashes == []
