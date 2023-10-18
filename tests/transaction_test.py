import pytest

from transaction_manager.structures import InvalidFormatError, Tx, TxStatus


def test_sample_tx():
    tx = Tx(
        tx_id='1232321332132131331321',
        status=TxStatus.PROPOSED,
        score=1,
        to='0x1',
        value=1,
        fee={'gas_price': 1000000000},
        gas=22000,
        nonce=3,
        method='createNode',
        source=None,
        tx_hash=None,
        data={'test': 1}
    )

    assert tx.hashes == []
    assert tx.raw_id == b'1232321332132131331321'
    assert not tx.is_sent()

    dumped_tx = tx.to_bytes()
    expected = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "maxFeePerGas": null, "maxPriorityFeePerGas": null, "meta": null, "method": "createNode", "multiplier": 1.2, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "tx_id": "1232321332132131331321", "value": 1}'  # noqa
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
        fee={'gas_price': 1000000000},
        gas=22000,
        nonce=3,
        data=None,
        tx_hash=None
    )
    assert not tx.is_completed()
    assert not tx.is_mined()
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
    tx.set_as_mined()
    assert tx.status == TxStatus.MINED
    tx.status = TxStatus.SENT
    tx.set_as_completed('tx-hash', 1)
    assert tx.status == TxStatus.SUCCESS
    tx.set_as_completed('tx-hash', 0)
    assert tx.status == TxStatus.FAILED
    tx.set_as_completed('tx-hash', -1)
    assert tx.status == TxStatus.FAILED


def test_tx_from_bytes():
    tx_id = b'tx-1232321332132131331321'

    with pytest.raises(InvalidFormatError):
        Tx.from_bytes(tx_id, b'')

    before_eip_1559 = b'{"attempts": 0, "status": "PROPOSED", "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "meta": null, "method": null, "nonce": 3, "score": 1, "sent_ts": null, "to": "0x1", "tx_hash": null, "value": 1}'  # noqa
    tx = Tx.from_bytes(tx_id, before_eip_1559)

    # sorted before_eip_1559 incuding eip_1559 fields
    expected = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "maxFeePerGas": null, "maxPriorityFeePerGas": null, "meta": null, "method": null, "multiplier": 1.2, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "tx_id": "tx-1232321332132131331321", "value": 1}'  # noqa
    assert tx.to_bytes() == expected

    missing_field_tx_id = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "maxFeePerGas": null, "maxPriorityFeePerGas": null, "meta": null, "method": null, "multiplier": 1.2, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "value": 1}'  # noqa
    tx = Tx.from_bytes(tx_id, missing_field_tx_id)
    # Same as missing_field_tx_id but with tx id
    expected = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "maxFeePerGas": null, "maxPriorityFeePerGas": null, "meta": null, "method": null, "multiplier": 1.2, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "tx_id": "tx-1232321332132131331321", "value": 1}'  # noqa
    assert tx.to_bytes() == expected

    missing_field_status = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "maxFeePerGas": 1000000000, "maxPriorityFeePerGas": 1000000000, "hashes": [], "meta": null, "method": null, "nonce": 3, "score": 1, "sent_ts": null, "to": "0x1", "tx_hash": null, "value": 1}'  # noqa

    with pytest.raises(InvalidFormatError):
        Tx.from_bytes(tx_id, missing_field_status)

    missing_field_to = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "maxFeePerGas": 1000000000, "maxPriorityFeePerGas": 1000000000, "from": null, "gas": 22000, "hashes": [], "meta": null, "method": null, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "tx_hash": null, "value": 1}'  # noqa

    with pytest.raises(InvalidFormatError):
        Tx.from_bytes(tx_id, missing_field_to)

    missing_field_hash = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "maxFeePerGas": 1000000000, "maxPriorityFeePerGas": 1000000000, "meta": null, "method": null, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "value": 1}'  # noqa
    tx = Tx.from_bytes(tx_id, missing_field_hash)
    assert tx.hashes == []

    with_type = b'{"attempts": 0, "type": "0x0", "status": "PROPOSED", "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "meta": null, "method": null, "nonce": 3, "score": 1, "sent_ts": null, "to": "0x1", "tx_hash": null, "value": 1}'  # noqa
    tx = Tx.from_bytes(tx_id, with_type)
    expected = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "maxFeePerGas": null, "maxPriorityFeePerGas": null, "meta": null, "method": null, "multiplier": 1.2, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "tx_id": "tx-1232321332132131331321", "value": 1}'  # noqa
    tx.to_bytes() == expected

    with_method_and_meta = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "maxFeePerGas": null, "maxPriorityFeePerGas": null, "meta": {"chain": "test"}, "method": "createNode", "multiplier": 1.2, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "tx_id": "tx-1232321332132131331321", "value": 1}'  # noqa
    tx = Tx.from_bytes(tx_id, with_method_and_meta)
    assert tx.to_bytes() == with_method_and_meta

    missing_method_and_meta = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "maxFeePerGas": null, "maxPriorityFeePerGas": null, "multiplier": 1.2, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "tx_id": "tx-1232321332132131331321", "value": 1}'  # noqa
    expected = b'{"attempts": 0, "chainId": null, "data": {"test": 1}, "from": null, "gas": 22000, "gasPrice": 1000000000, "hashes": [], "maxFeePerGas": null, "maxPriorityFeePerGas": null, "meta": null, "method": null, "multiplier": 1.2, "nonce": 3, "score": 1, "sent_ts": null, "status": "PROPOSED", "to": "0x1", "tx_hash": null, "tx_id": "tx-1232321332132131331321", "value": 1}'  # noqa
    tx = Tx.from_bytes(tx_id, missing_method_and_meta)
    actual = tx.to_bytes()
    assert actual == expected


def test_is_sent_by_ima():
    tx = Tx(
        tx_id='tx-72c337ab0ac56aa8js',
        status=TxStatus.PROPOSED,
        score=1,
        to='0x1',
        value=1,
        fee={'gas_price': 1000000000},
        gas=22000,
        nonce=3,
        source=None,
        tx_hash=None,
        data={'test': 1}
    )
    assert tx.is_sent_by_ima()

    tx.tx_id = 'tx-cfada2025eb7d62e'
    assert not tx.is_sent_by_ima()
