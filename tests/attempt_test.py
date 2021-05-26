import pytest

from transaction_manager.attempt import (
    Attempt,
    GasPriceLimitExceededError,
    get_last_attempt,
    make_next_attempt,
    set_last_attempt
)


def create_attempt():
    tid = 'id-aaaa'
    return Attempt(
        tx_id=tid,
        nonce=1,
        index=2,
        gas_price=10 ** 9,
        wait_time=30
    )


def test_attempt():
    aa = create_attempt()
    assert aa.nonce == 1
    assert aa.index == 2
    assert aa.tx_id == 'id-aaaa'
    assert aa.gas_price == 10 ** 9
    assert aa.wait_time == 30

    aa_raw = aa.to_bytes()
    assert aa_raw == b'{"tx_id": "id-aaaa", "nonce": 1, "index": 2, "gas_price": 1000000000, "wait_time": 30}'  # noqa
    assert Attempt.from_bytes(aa_raw) == aa


def test_get_set_last_attempt(trs):
    assert get_last_attempt(rs=trs) is None
    aa = create_attempt()
    set_last_attempt(aa, rs=trs)
    assert get_last_attempt(rs=trs) == aa


def test_make_next_attempt():
    aa = create_attempt()
    bb = make_next_attempt(
        nonce=aa.nonce,
        avg_gas_price=10 ** 9,
        tx_id=aa.tx_id,
        last=aa
    )
    assert bb.tx_id == aa.tx_id
    assert bb.gas_price == 1100000000
    assert bb.nonce == aa.nonce
    assert bb.index == aa.index + 1
    assert bb.wait_time == 40

    cc_tid = 'id-cccc'
    cc = make_next_attempt(
        nonce=bb.nonce + 1,
        avg_gas_price=10 ** 9,
        tx_id=cc_tid,
        last=bb
    )
    assert cc.tx_id == cc_tid
    assert cc.gas_price == 10 ** 9
    assert cc.nonce == bb.nonce + 1
    assert cc.index == 1
    assert cc.wait_time == 10

    dd_tid = 'id-dddd'
    dd = make_next_attempt(
        nonce=0,
        avg_gas_price=10 ** 9,
        tx_id=dd_tid,
        last=None
    )
    assert dd.tx_id == dd_tid
    assert dd.gas_price == 10 ** 9
    assert dd.nonce == 0
    assert dd.index == 1

    dd.gas_price = 3 * 10 ** 9 - 100

    ee_tid = 'id-eeee'
    with pytest.raises(GasPriceLimitExceededError):
        make_next_attempt(
            nonce=0,
            avg_gas_price=10 ** 9,
            tx_id=ee_tid,
            last=dd
        )
