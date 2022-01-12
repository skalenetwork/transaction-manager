import pytest

from transaction_manager.attempt_manager.base import NoCurrentAttemptError
from transaction_manager.attempt_manager import AttemptManagerV1
from transaction_manager.config import (
    GAS_PRICE_INC_PERCENT, GRAD_GAS_PRICE_INC_PERCENT
)
from transaction_manager.structures import Attempt, Fee, Tx, TxStatus


def create_attempt(nonce=1, index=2, gas_price=10 ** 9, wait_time=30):
    tid = 'id-aaaa'
    return Attempt(
        tx_id=tid,
        nonce=nonce,
        index=index,
        fee=Fee(gas_price=gas_price),
        wait_time=wait_time
    )


@pytest.fixture
def attempt_manager(eth, attempt_storage, wallet):
    return AttemptManagerV1(eth, attempt_storage, wallet.address)


def test_v1_make(w3, eth, attempt_manager, wallet):
    acc = w3.eth.account.create()
    addr, _ = acc.address, acc.key.hex()
    initial_gas = 21000

    tx = Tx(
        tx_id='1232321332132131331321',
        chain_id=eth.chain_id,
        status=TxStatus.PROPOSED,
        score=1,
        to=addr,
        value=1,
        fee={'gas_price': 1000000000},
        gas=21000,
        nonce=0,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )
    attempt_manager.make(tx)
    assert attempt_manager.current.tx_id == tx.tx_id
    assert attempt_manager.current.index == 1

    initial_gp = 2 * 10 ** 9
    aa = create_attempt(gas_price=initial_gp, index=2)
    attempt_manager._current = aa

    tx = Tx(
        tx_id='1232321332132131331321',
        chain_id=31337,
        status=TxStatus.PROPOSED,
        score=1,
        to=addr,
        value=1,
        fee={'gas_price': 1000000000},
        gas=initial_gas,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )
    attempt_manager.current.nonce = eth.get_nonce(wallet.address)
    attempt_manager.make(tx)
    assert attempt_manager.current.tx_id == tx.tx_id
    new_gp = initial_gp * (100 + GAS_PRICE_INC_PERCENT) // 100
    assert attempt_manager.current.fee.gas_price == new_gp
    assert attempt_manager.current.gas > initial_gas
    assert tx.gas == attempt_manager.current.gas
    assert attempt_manager.current.tx_id == tx.tx_id
    assert attempt_manager.current.index == 3

    attempt_manager.current.fee.gas_price = attempt_manager.max_gas_price
    attempt_manager.make(tx)
    assert attempt_manager.current.fee.gas_price == attempt_manager.max_gas_price  # noqa
    assert attempt_manager.current.index == 4


def test_v1_replace(w3, eth, attempt_manager):
    acc = w3.eth.account.create()
    addr, _ = acc.address, acc.key.hex()

    tx = Tx(
        tx_id='1232321332132131331321',
        chain_id=31337,
        status=TxStatus.PROPOSED,
        score=1,
        to=addr,
        value=1,
        fee={'gas_price': 1000000000},
        gas=21000,
        nonce=0,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )

    with pytest.raises(NoCurrentAttemptError):
        attempt_manager.replace(tx)

    initial_gp = 2 * 10 ** 9
    aa = create_attempt(gas_price=initial_gp, index=2)
    attempt_manager._current = aa

    tx = Tx(
        tx_id='1232321332132131331321',
        chain_id=31337,
        status=TxStatus.PROPOSED,
        score=1,
        to=addr,
        value=1,
        fee={'gas_price': 1000000000},
        gas=21000,
        nonce=0,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )

    attempt_manager.replace(tx)
    assert attempt_manager.current.tx_id == aa.tx_id
    new_gp = initial_gp * (100 + GRAD_GAS_PRICE_INC_PERCENT) // 100
    assert attempt_manager.current.fee.gas_price == new_gp
    assert attempt_manager.current.index == 2

    attempt_manager.current.fee.gas_price = attempt_manager.max_gas_price
    attempt_manager.replace(tx)
    assert attempt_manager.current.fee.gas_price == attempt_manager.max_gas_price  # noqa
    assert attempt_manager.current.index == 2


def test_v1_save_fetch(w3, attempt_manager):
    sample_attempt = create_attempt()
    attempt_manager._current = sample_attempt
    attempt_manager.save()
    attempt_manager.fetch()
    assert attempt_manager._current == sample_attempt
