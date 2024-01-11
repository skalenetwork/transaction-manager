import pytest
from unittest.mock import Mock
from skale.utils.account_tools import send_eth

from transaction_manager.attempt_manager.base import NoCurrentAttemptError
from transaction_manager.attempt_manager.v2 import AttemptManagerV2
from transaction_manager.config import MAX_FEE_VALUE
from transaction_manager.structures import Attempt, Fee, Tx, TxStatus

TEST_ETH_VALUE = 2

BASE_FEE_VALUE = 10 ** 11
P50_REWARD = 10 ** 8
P60_REWARD = 10 ** 9


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
    send_eth(w3, wallet, acc.address, TEST_ETH_VALUE)
    return acc.address, acc.key.hex()


def test_v2_max_allowed_fee(w3, eth, attempt_manager, wallet, account):
    attempt_manager.source, _ = account
    gas = 1000000
    value = TEST_ETH_VALUE // 2 * 10 ** 18
    assert attempt_manager.max_allowed_fee(gas, value) == 1000000000000
    value = TEST_ETH_VALUE * 10 ** 18
    assert attempt_manager.max_allowed_fee(gas, value) == 0


@pytest.fixture
def history_eth(eth):
    eth.get_fee_history = Mock(
        return_value={
            'baseFeePerGas': [BASE_FEE_VALUE / 10, BASE_FEE_VALUE],
            'reward': [[P50_REWARD, P60_REWARD]]}
    )
    return eth


def test_v2_make(w3, history_eth, attempt_manager, account, wallet):
    attempt_manager.eth = history_eth
    eth = history_eth
    chain_id = eth.chain_id
    addr, _ = account
    a_id = 'A_ID'

    # Attempt with no last
    attempt_manager._current = None
    tx = Tx(
        tx_id=a_id,
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
    current = attempt_manager.current
    expected_tip = P60_REWARD
    expected_gap = (BASE_FEE_VALUE * 150) // 100
    # Id should be the same
    assert current.tx_id == tx.tx_id == a_id
    # Tip should be equal to good reward
    assert tx.fee.max_priority_fee_per_gas == current.fee.max_priority_fee_per_gas == expected_tip   # noqa
    # Gap should be 150 % of estimated_base_fee
    assert tx.fee.max_fee_per_gas == current.fee.max_fee_per_gas == expected_gap  # noqa
    # Gas should be estimated
    assert tx.gas == current.gas and tx.gas > 0
    # Index should be estimated
    assert current.index == 1
    # Index should be estimated
    assert tx.nonce == current.nonce and tx.nonce == eth.get_nonce(wallet.address)  # noqa

    a_sent_fee = tx.fee

    # Test another attempt with new transaction with same nonce and static gas
    b_id = 'B_ID'
    initial_gas = 31000
    tx = Tx(
        tx_id=b_id,
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
    current = attempt_manager.current
    expected_tip = (P60_REWARD * 112) // 100
    expected_gap = (BASE_FEE_VALUE * 150 // 100) * 112 // 100

    # Id should be the same
    assert current.tx_id == tx.tx_id == b_id
    # Tip should be equal to good reward
    assert tx.fee.max_priority_fee_per_gas == current.fee.max_priority_fee_per_gas == expected_tip   # noqa
    # Gap should be 150 % of estimated_base_fee
    assert tx.fee.max_fee_per_gas == current.fee.max_fee_per_gas == expected_gap  # noqa
    # Gas should be estimated
    assert tx.gas == current.gas and tx.gas == initial_gas
    # Since it's another attempt index should be 2
    assert current.index == 2
    # Index should be estimated
    assert tx.nonce == current.nonce and tx.nonce == eth.get_nonce(wallet.address)  # noqa

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
    current = attempt_manager.current
    expected_tip = P60_REWARD
    expected_gap = (BASE_FEE_VALUE * 150) // 100

    # Id should be the same
    assert current.tx_id == tx.tx_id == a_id
    # Tip should be equal to good reward
    assert tx.fee.max_priority_fee_per_gas == current.fee.max_priority_fee_per_gas == expected_tip   # noqa
    # Gap should be 150 % of estimated_base_fee
    assert tx.fee.max_fee_per_gas == current.fee.max_fee_per_gas == expected_gap  # noqa
    # Gas should be estimated
    assert tx.gas == current.gas and tx.gas > 0
    # Since nonce was increased index should be 1
    assert current.index == 1
    # Nonce should be equal to getTransactionCount
    assert tx.nonce == current.nonce and tx.nonce == eth.get_nonce(wallet.address)  # noqa

    # Test next attempt with fee that is more than max
    attempt_manager.current.fee.max_priority_fee_per_gas = MAX_FEE_VALUE - 1
    attempt_manager.current.fee.max_fee_per_gas = MAX_FEE_VALUE - 1
    attempt_manager.make(tx)
    expected_tip, expected_gap = MAX_FEE_VALUE, MAX_FEE_VALUE
    current = attempt_manager.current
    assert tx.fee.max_priority_fee_per_gas == current.fee.max_priority_fee_per_gas == expected_tip   # noqa
    # Gap should be 150 % of estimated_base_fee
    assert tx.fee.max_fee_per_gas == current.fee.max_fee_per_gas == expected_gap  # noqa
    # Nonce should be equal to getTransactionCount
    assert tx.nonce == attempt_manager.current.nonce == eth.get_nonce(wallet.address)  # noqa
    # Since it's another attempt index should be 2
    assert current.index == 2

    # Test next attempt with transaction that was already sent
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
    # Emulates that account successfully sent another transaction
    attempt_manager._current.nonce = eth.get_nonce(wallet.address) - 1
    attempt_manager.make(tx)
    current = attempt_manager.current

    expected_tip = P60_REWARD
    expected_gap = (BASE_FEE_VALUE * 150) // 100
    # Id should be the same
    assert current.tx_id == tx.tx_id == a_id
    # Tip should be equal to good reward
    assert tx.fee.max_priority_fee_per_gas == current.fee.max_priority_fee_per_gas == expected_tip   # noqa
    # Gap should be 150 % of estimated_base_fee
    assert tx.fee.max_fee_per_gas == current.fee.max_fee_per_gas == expected_gap  # noqa
    # Gas should be estimated
    assert tx.gas == current.gas and tx.gas > 0
    # Since nonce was increased index should be 1
    assert current.index == 1
    assert tx.nonce == current.nonce and tx.nonce == eth.get_nonce(wallet.address)  # noqa


def test_v2_make_low_static_gas(w3, eth, attempt_manager, account, wallet):
    chain_id = eth.chain_id
    addr, _ = account
    a_id = 'A_ID'
    static_gas = 22000

    attempt_manager._current = None

    tx = Tx(
        tx_id=a_id,
        chain_id=chain_id,
        status=TxStatus.PROPOSED,
        score=1,
        to=addr,
        value=1,
        fee=None,
        gas=static_gas,
        source=addr,
        tx_hash=None,
        data=None,
        multiplier=1.2
    )
    attempt_manager.make(tx)
    current = attempt_manager.current
    # Id should be the same
    assert current.tx_id == tx.tx_id == a_id
    # Tip should be equal to good reward
    assert current.gas == tx.gas > static_gas


def test_v2_make_iterative(w3, history_eth, attempt_manager, account, wallet):
    attempt_manager.eth = history_eth
    eth = history_eth
    chain_id = eth.chain_id
    addr, _ = account
    a_id = 'A_ID'
    # Attempt with no last
    attempt_manager._current = None
    attempt_manager.max_fee = 280000000000
    tx = Tx(
        tx_id=a_id,
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
    expected_tip = P60_REWARD
    expected_gap = (BASE_FEE_VALUE * 150) // 100

    for i in range(6):
        attempt_manager.make(tx)
        assert tx.fee.max_priority_fee_per_gas == expected_tip, i
        assert tx.fee.max_fee_per_gas == expected_gap, i
        expected_tip = (expected_tip * 112) // 100
        expected_gap = (expected_gap * 112) // 100

    attempt_manager.make(tx)
    assert tx.fee.max_priority_fee_per_gas == expected_tip
    assert tx.fee.max_fee_per_gas == attempt_manager.max_fee


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


def test_v2_replace(w3, history_eth, attempt_manager, account):
    eth = history_eth
    attempt_manager.eth = history_eth
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

    # Replace without previous attempt should raise error
    with pytest.raises(NoCurrentAttemptError):
        attempt_manager.replace(tx)

    attempt_manager.make(tx)

    # Replace with previous attempt
    attempt_manager.replace(tx)
    current = attempt_manager.current
    expected_tip = P60_REWARD * 105 // 100
    expected_gap = (BASE_FEE_VALUE * 150) // 100 * 105 // 100
    assert tx.fee.max_priority_fee_per_gas == current.fee.max_priority_fee_per_gas == expected_tip  # noqa
    assert tx.fee.max_fee_per_gas == current.fee.max_fee_per_gas == expected_gap  # noqa

    # Test replace with max allowed value
    tx.fee.max_priority_fee_per_gas = MAX_FEE_VALUE - 1
    tx.fee.max_fee_per_gas = MAX_FEE_VALUE - 1
    attempt_manager.replace(tx)
    current = attempt_manager.current
    assert tx.fee.max_priority_fee_per_gas == current.fee.max_priority_fee_per_gas == MAX_FEE_VALUE  # noqa
    assert tx.fee.max_fee_per_gas == current.fee.max_fee_per_gas == MAX_FEE_VALUE  # noqa


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
