import pytest

from transaction_manager.attempt_manager.base import NoCurrentAttemptError
from transaction_manager.config import (
    BASE_PRIORITY_FEE,
    MAX_FEE_VALUE,
    MAX_PRIORITY_FEE_VALUE
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
def account(w3):
    acc = w3.eth.account.create()
    return acc.address, acc.key.hex()


def test_v2_make(w3, eth, attempt_manager, account, wallet):
    chain_id = 31337
    initial_gas = 21000
    addr, _ = account
    a_id = 'A_ID'

    # Test attempt with no last
    tx = Tx(
        tx_id=a_id,
        chain_id=chain_id,
        status=TxStatus.PROPOSED,
        score=1,
        to=addr,
        value=1,
        fee=None,
        gas=initial_gas,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )
    attempt_manager.make(tx)
    assert attempt_manager.current.tx_id == a_id
    assert attempt_manager.current.fee.max_priority_fee_per_gas == BASE_PRIORITY_FEE   # noqa
    assert attempt_manager.current.gas == initial_gas
    assert attempt_manager.current.index == 1
    attempt_manager.current.nonce == eth.get_nonce(wallet.address)

    a_sent_fee = tx.fee

    # Test another attempt with new transaction
    b_id = 'B_ID'
    tx = Tx(
        tx_id=b_id,
        chain_id=chain_id,
        status=TxStatus.PROPOSED,
        score=1,
        to=addr,
        value=1,
        fee=None,
        gas=None,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )
    attempt_manager.make(tx)
    new_fee_val = (BASE_PRIORITY_FEE * 110) // 100

    assert attempt_manager.current.tx_id == tx.tx_id
    assert attempt_manager.current.fee.max_priority_fee_per_gas == new_fee_val
    assert tx.gas == attempt_manager.current.gas
    assert tx.gas != initial_gas
    assert attempt_manager.current.tx_id == b_id
    assert attempt_manager.current.index == 2
    attempt_manager.current.nonce == eth.get_nonce(wallet.address)

    # Test next attempt with transaction that was already sent
    tx = Tx(
        tx_id=a_id,
        chain_id=chain_id,
        status=TxStatus.SENT,
        score=1,
        to=addr,
        value=1,
        fee=a_sent_fee,
        gas=initial_gas,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )
    attempt_manager.current.nonce -= 1
    attempt_manager.make(tx)
    attempt_manager.current.fee.max_priority_fee_per_gas == BASE_PRIORITY_FEE
    attempt_manager.current.tx_id == a_id
    attempt_manager.current.nonce == eth.get_nonce(wallet.address)
    assert attempt_manager.current.index == 1

    # Test next attempt with fee that is more than max
    attempt_manager.current.fee.max_priority_fee_per_gas = MAX_FEE_VALUE
    attempt_manager.make(tx)
    assert attempt_manager.current.fee.max_priority_fee_per_gas == MAX_PRIORITY_FEE_VALUE  # noqa
    assert attempt_manager.current.tx_id == a_id
    attempt_manager.current.nonce == eth.get_nonce(wallet.address)
    assert attempt_manager.current.index == 2


def test_v2_fetch_save(w3, eth, attempt_manager, account):
    # Fetch with empty data
    attempt_manager.fetch()
    assert attempt_manager._current is None

    chain_id = 31337
    initial_gas = 21000
    addr, _ = account
    a_id = 'A_ID'

    # Test attempt with no last
    tx = Tx(
        tx_id=a_id,
        chain_id=chain_id,
        status=TxStatus.PROPOSED,
        score=1,
        to=addr,
        value=1,
        fee=None,
        gas=initial_gas,
        nonce=0,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )
    attempt_manager.make(tx)
    attempt_manager.save()

    attempt = attempt_manager._current
    attempt_manager._current = None
    attempt_manager.fetch()
    assert attempt_manager._current == attempt


def test_v2_replace(w3, eth, attempt_manager, account):
    chain_id = 31337
    initial_gas = 21000
    addr, _ = account
    a_id = 'A_ID'

    # Test attempt with no last
    tx = Tx(
        tx_id=a_id,
        chain_id=chain_id,
        status=TxStatus.PROPOSED,
        score=1,
        to=addr,
        value=1,
        fee=None,
        gas=initial_gas,
        nonce=0,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )

    with pytest.raises(NoCurrentAttemptError):
        attempt_manager.replace(tx)

    attempt_manager.make(tx)
    attempt_manager.replace(tx)
    expected_pf = BASE_PRIORITY_FEE * 110 // 100
    assert attempt_manager.current.fee.max_priority_fee_per_gas == expected_pf

    tx.fee.max_priority_fee_per_gas = MAX_PRIORITY_FEE_VALUE
    assert tx.fee.max_fee_per_gas == MAX_FEE_VALUE
    attempt_manager.current.fee.max_priority_fee_per_gas = MAX_FEE_VALUE  # noqa
    attempt_manager.replace(tx)
    assert attempt_manager.current.fee.max_priority_fee_per_gas == MAX_PRIORITY_FEE_VALUE  # noqa
