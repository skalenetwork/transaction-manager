from transaction_manager.attempt import (
    Attempt,
    AttemptManager,
    get_last_attempt,
    MAX_GAS_PRICE,
    MIN_GAS_PRICE_INC,
    set_last_attempt
)
from transaction_manager.transaction import Fee


def create_attempt(nonce=1, index=2, gas_price=10 ** 9, wait_time=30):
    tid = 'id-aaaa'
    return Attempt(
        tx_id=tid,
        nonce=nonce,
        index=index,
        fee=Fee(gas_price=1000000000),
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
    expected = b'{"fee": {"gas_price": 1000000000, "max_fee_per_gas": null, "max_priority_fee_per_gas": null}, "index": 2, "nonce": 1, "tx_id": "id-aaaa", "wait_time": 30}'  # noqa
    print(aa_raw)
    print(expected)
    assert aa_raw == expected
    assert Attempt.from_bytes(aa_raw) == aa

    raw_before_eip_1559 = b'{"gas_price": 1000000000, "index": 2, "nonce": 1, "tx_id": "id-aaaa", "wait_time": 30}'  # noqa
    attempt = Attempt.from_bytes(raw_before_eip_1559)
    assert attempt.to_bytes() == expected


def test_get_set_last_attempt(trs):
    assert get_last_attempt(rs=trs) is None
    aa = create_attempt()
    set_last_attempt(aa, rs=trs)
    assert get_last_attempt(rs=trs) == aa


def attempt_manager_next_attempt(eth):
    attempt_manager = AttemptManager(eth)
    aa = create_attempt()
    # Basic test
    bb = attempt_manager.next_attempt(
        nonce=aa.nonce,
        avg_gas_price=10 ** 9,
        tx_id=aa.tx_id,
        last=aa
    )
    assert bb.tx_id == aa.tx_id
    assert bb.gas_price == 1100000000
    assert bb.nonce == aa.nonce
    assert bb.index == aa.index + 1
    assert bb.wait_time == 110

    cc_tid = 'id-cccc'
    cc = attempt_manager.next_attempt(
        nonce=bb.nonce + 1,
        avg_gas_price=10 ** 9,
        tx_id=cc_tid,
        last=bb
    )
    assert cc.tx_id == cc_tid
    assert cc.gas_price == 10 ** 9
    assert cc.nonce == bb.nonce + 1
    assert cc.index == 1
    assert cc.wait_time == 20

    dd_tid = 'id-dddd'
    dd = attempt_manager.next_attempt(
        nonce=0,
        avg_gas_price=10 ** 9,
        tx_id=dd_tid,
        last=None
    )
    assert dd.tx_id == dd_tid
    assert dd.gas_price == 10 ** 9
    assert dd.nonce == 0
    assert dd.index == 1

    dd.gas_price = 1000 * 10 ** 9 - 100

    ee_tid = 'id-eeee'
    ee = attempt_manager.next_attempt(
        nonce=0,
        avg_gas_price=10 ** 9,
        tx_id=ee_tid,
        last=dd
    )
    assert ee.gas_price == MAX_GAS_PRICE


def test_create_next_attempt_small_gas_price(eth):
    attempt_manager = AttemptManager(eth)
    initial_gp = 1
    aa = create_attempt(gas_price=initial_gp)
    bb = attempt_manager.next_attempt(
        nonce=aa.nonce,
        avg_gas_price=initial_gp,
        tx_id=aa.tx_id,
        last=aa
    )
    assert bb.tx_id == aa.tx_id
    assert bb.gas_price == initial_gp + MIN_GAS_PRICE_INC
