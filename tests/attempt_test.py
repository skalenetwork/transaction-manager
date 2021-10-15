from transaction_manager.attempt import (
    Attempt,
    create_next_attempt,
    get_last_attempt,
    MAX_GAS_PRICE,
    MIN_GAS_PRICE_INC,
    set_last_attempt
)


def create_attempt(nonce=1, index=2, gas_price=10 ** 9, wait_time=30):
    tid = 'id-aaaa'
    return Attempt(
        tx_id=tid,
        nonce=nonce,
        index=index,
        gas_price=gas_price,
        wait_time=wait_time
    )


def test_attempt():
    aa = create_attempt()
    assert aa.nonce == 1
    assert aa.index == 2
    assert aa.tx_id == 'id-aaaa'
    assert aa.gas_price == 10 ** 9
    assert aa.wait_time == 30

    aa_raw = aa.to_bytes()
    expected = b'{"gas_price": 1000000000, "index": 2, "nonce": 1, "tx_id": "id-aaaa", "wait_time": 30}'  # noqa
    assert aa_raw == expected
    assert Attempt.from_bytes(aa_raw) == aa


def test_get_set_last_attempt(trs):
    assert get_last_attempt(rs=trs) is None
    aa = create_attempt()
    set_last_attempt(aa, rs=trs)
    assert get_last_attempt(rs=trs) == aa


def test_create_next_attempt():
    aa = create_attempt()
    bb = create_next_attempt(
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
    cc = create_next_attempt(
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
    dd = create_next_attempt(
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
    ee = create_next_attempt(
        nonce=0,
        avg_gas_price=10 ** 9,
        tx_id=ee_tid,
        last=dd
    )
    assert ee.gas_price == MAX_GAS_PRICE


def test_create_next_attempt_small_gas_price():
    initial_gp = 1
    aa = create_attempt(gas_price=initial_gp)
    bb = create_next_attempt(
        nonce=aa.nonce,
        avg_gas_price=initial_gp,
        tx_id=aa.tx_id,
        last=aa
    )
    assert bb.tx_id == aa.tx_id
    assert bb.gas_price == initial_gp + MIN_GAS_PRICE_INC
