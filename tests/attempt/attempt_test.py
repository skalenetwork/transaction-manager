from transaction_manager.structures import Attempt, Fee


def create_attempt(nonce=1, index=2, gas_price=10 ** 9, wait_time=30):
    tid = 'id-aaaa'
    return Attempt(
        tx_id=tid,
        nonce=nonce,
        index=index,
        fee=Fee(gas_price=gas_price),
        wait_time=wait_time
    )


def test_attempt():
    aa = create_attempt()
    assert aa.nonce == 1
    assert aa.index == 2
    assert aa.tx_id == 'id-aaaa'
    assert aa.fee.gas_price == 10 ** 9
    assert aa.wait_time == 30

    aa_raw = aa.to_bytes()
    expected = b'{"fee": {"gas_price": 1000000000, "max_fee_per_gas": null, "max_priority_fee_per_gas": null}, "gas": null, "index": 2, "nonce": 1, "tx_id": "id-aaaa", "wait_time": 30}'  # noqa
    print(aa_raw)
    assert aa_raw == expected
    assert Attempt.from_bytes(aa_raw) == aa

    raw_before_eip_1559 = b'{"gas_price": 1000000000, "index": 2, "nonce": 1, "tx_id": "id-aaaa", "wait_time": 30}'  # noqa
    attempt = Attempt.from_bytes(raw_before_eip_1559)
    assert attempt.to_bytes() == expected
