import pytest
from mock import Mock
from skale.utils.account_tools import send_ether

from transaction_manager.attempt_manager.base import NoCurrentAttemptError
from transaction_manager.attempt_manager.v2 import AttemptManagerV2
from transaction_manager.config import MAX_FEE_VALUE, MIN_PRIORITY_FEE
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
def account(w3, wallet):
    acc = w3.eth.account.create()
    send_ether(w3, wallet, acc.address, 2)
    return acc.address, acc.key.hex()


def test_v2_make(w3, eth, attempt_manager, account, wallet):
    chain_id = eth.chain_id
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
    assert attempt_manager.current.fee.max_priority_fee_per_gas == MIN_PRIORITY_FEE   # noqa
    assert attempt_manager.current.fee.max_fee_per_gas == (MIN_PRIORITY_FEE * 150) // 100  # noqa
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
    new_tip_val = (MIN_PRIORITY_FEE * 115) // 100
    new_cap_val = (MIN_PRIORITY_FEE * 150 // 100) * 115 // 100

    assert attempt_manager.current.tx_id == tx.tx_id
    assert attempt_manager.current.fee.max_priority_fee_per_gas == new_tip_val
    assert attempt_manager.current.fee.max_fee_per_gas == new_cap_val
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
    attempt_manager.current.fee.max_priority_fee_per_gas == MIN_PRIORITY_FEE
    attempt_manager.current.tx_id == a_id
    attempt_manager.current.nonce == eth.get_nonce(wallet.address)
    assert attempt_manager.current.index == 1

    # Test next attempt with fee that is more than max
    attempt_manager.current.fee.max_priority_fee_per_gas = MAX_FEE_VALUE - 1
    attempt_manager.current.fee.max_fee_per_gas = MAX_FEE_VALUE - 1
    attempt_manager.make(tx)
    assert attempt_manager.current.fee.max_fee_per_gas == MAX_FEE_VALUE
    assert attempt_manager.current.fee.max_priority_fee_per_gas == MAX_FEE_VALUE  # noqa
    assert attempt_manager.current.tx_id == a_id
    attempt_manager.current.nonce == eth.get_nonce(wallet.address)
    assert attempt_manager.current.index == 2

    # Test next attempt with transaction that was already sent
    eth.fee_history = Mock(
        return_value={'baseFeePerGas': [10, 10 ** 10], 'reward': [[5 * 10 ** 9, 6 * 10 ** 9]]}  # noqa
    )
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
    attempt_manager._current.nonce = eth.get_nonce(wallet.address) - 1
    attempt_manager.make(tx)
    assert attempt_manager.current.fee.max_priority_fee_per_gas == 6 * 10 ** 9
    assert attempt_manager.current.fee.max_fee_per_gas == 15000000000  # noqa


def test_v2_fetch_save(w3, eth, attempt_manager, account):
    # Fetch with empty data
    attempt_manager.fetch()
    assert attempt_manager._current is None

    chain_id = eth.chain_id
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
    chain_id = eth.chain_id
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
    expected_pf = MIN_PRIORITY_FEE * 112 // 100
    assert attempt_manager.current.fee.max_priority_fee_per_gas == expected_pf

    tx.fee.max_priority_fee_per_gas = MAX_FEE_VALUE
    tx.fee.max_fee_per_gas = MAX_FEE_VALUE
    attempt_manager.replace(tx)
    assert attempt_manager.current.fee.max_fee_per_gas == MAX_FEE_VALUE
    assert attempt_manager.current.fee.max_priority_fee_per_gas == MAX_FEE_VALUE  # noqa


def test_v2_make_with_low_balance(w3, eth, attempt_storage, wallet, account):
    addr, _ = account
    chain_id = eth.chain_id
    initial_gas = 21000
    addr, _ = account
    a_id = 'A_ID'

    attempt_manager = AttemptManagerV2(eth, attempt_storage, addr)

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
    tx.fee.max_priority_fee_per_gas += 1
    attempt_manager.replace(tx)
