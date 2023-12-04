from unittest import mock
import pytest

from transaction_manager.config import MAX_RESUBMIT_AMOUNT
from transaction_manager.eth import EstimateGasRevertError
from transaction_manager.processor import Processor, SendingError
from transaction_manager.structures import TxStatus

from tests.utils.contracts import get_tester_abi
from tests.utils.timing import in_time

DEFAULT_GAS = 20000


@pytest.fixture
def proc(tpool, eth, trs, attempt_manager, wallet):
    return Processor(eth, tpool, attempt_manager, wallet)


@pytest.fixture
def proc_v1(tpool, eth, trs, attempt_manager_v1, wallet):
    return Processor(eth, tpool, attempt_manager_v1, wallet)


def make_tx(w3, wallet, failed=False):
    tester_abi = get_tester_abi()
    tester = w3.eth.contract(
        abi=tester_abi['abi'],
        address=tester_abi['address']
    )
    number = 3 if failed else 4
    return tester.functions.setOnlyEven(
        number
    ).build_transaction({
        'gasPrice': w3.eth.gas_price,
        'gas': DEFAULT_GAS,
        'from': wallet.address
    })


def push_tx(w3, rdp, tpool, wallet, failed=False):
    tx = make_tx(w3, wallet, failed=failed)
    tx_id = rdp.sign_and_send(tx)
    raw_id = tx_id.encode('utf-8')
    return tpool.get(raw_id)


def push_ima_tx(w3, rdp, tpool, wallet, failed=False):
    tx = push_tx(w3, rdp, tpool, wallet, failed=failed)
    tx.tx_id = tx.tx_id + 'js'
    return tx


def get_from_pool(tx_id, tpool):
    raw_id = tx_id.encode('utf-8')
    return tpool.get(raw_id)


class ProcTestError(Exception):
    pass


def test_processor_acquire_tx(proc, tpool, eth, trs, w3, wallet, rdp):
    tx = push_tx(w3, rdp, tpool, wallet)
    with proc.acquire_tx(tx):
        tx.status = TxStatus.SUCCESS
    assert get_from_pool(tx.tx_id, tpool).status == TxStatus.SUCCESS

    try:
        with proc.acquire_tx(tx):
            tx.status = TxStatus.SENT
            raise ProcTestError('Test error')
    except ProcTestError:
        assert get_from_pool(tx.tx_id, tpool).status == TxStatus.SENT

    tx = get_from_pool(tx.tx_id, tpool)
    tx.attempts = MAX_RESUBMIT_AMOUNT

    with proc.acquire_tx(tx):
        tx.status = TxStatus.TIMEOUT
    tx = get_from_pool(tx.tx_id, tpool)
    assert tx.status == TxStatus.DROPPED

    with proc.acquire_tx(tx):
        tx.status = TxStatus.SUCCESS
    tx = get_from_pool(tx.tx_id, tpool)
    assert tx.status == TxStatus.SUCCESS


def test_get_exec_data(proc, w3, rdp, eth, tpool, wallet):
    tx = push_tx(w3, rdp, tpool, wallet)
    tx.hashes = ['0x1234', '0x1235', '0x12346']
    tx.attempts = 3
    eth.get_status = mock.Mock(return_value=-1)
    h, r = proc.get_exec_data(tx)
    assert r is None and h is None

    eth.get_status = mock.Mock(return_value=1)
    h, r = proc.get_exec_data(tx)
    assert r == 1 and h == '0x12346'


def test_send(proc, w3, rdp, eth, tpool, wallet):
    tx = push_tx(w3, rdp, tpool, wallet)
    tx.chain_id = eth.chain_id
    tx.nonce = 0
    proc.attempt_manager.make(tx)

    proc.eth.send_tx = mock.Mock(
        side_effect=ValueError('unknown error')
    )
    with pytest.raises(SendingError):
        proc.send(tx)
    # Test that attempt was not saved if it was neither sent or replaced
    assert proc.attempt_manager.storage.get() is None
    assert tx.tx_hash is None
    assert tx.hashes == []

    proc.eth.send_tx = mock.Mock(
        side_effect=ValueError({
                'code': -32000,
                'message': 'replacement transaction underpriced'
            })
    )
    with pytest.raises(SendingError):
        proc.send(tx)
    # Test that attempt was saved if it was replaced
    assert proc.attempt_manager.storage.get().fee == tx.fee
    assert tx.tx_hash is None
    assert tx.hashes == []

    proc.eth.send_tx = mock.Mock(return_value='0x12323213213321321')
    proc.send(tx)
    assert tx.tx_hash == '0x12323213213321321'
    assert tx.hashes == ['0x12323213213321321']

    proc.eth.send_tx = mock.Mock(return_value='0x213812903813123')
    proc.send(tx)
    # Test that attempt was saved if it was sent
    assert proc.attempt_manager.storage.get().fee == tx.fee
    assert tx.tx_hash == '0x213812903813123'
    assert tx.hashes == ['0x12323213213321321', '0x213812903813123']


def test_process_tx(proc, w3, tpool, eth, trs, wallet, rdp):
    tx = push_tx(w3, rdp, tpool, wallet)
    proc.process(tx)
    assert tx.tx_hash is not None
    assert tx.hashes == [tx.tx_hash]
    assert tx.status == TxStatus.SUCCESS

    tx = push_tx(w3, rdp, tpool, wallet)
    tx.to = 'bad-address'
    with pytest.raises(Exception):
        proc.process(tx)


@pytest.mark.skip('Geth only test')
def test_send_replacement_underpriced(proc, w3, rdp, eth, tpool, wallet):
    tx = push_tx(w3, rdp, tpool, wallet)
    tx.chain_id = eth.chain_id
    tx.nonce = 0
    proc.attempt_manager.make(tx)

    proc.send(tx)
    tx.fee.max_priority_fee_per_gas += 1000
    tx.fee.max_fee_per_gas -= 1000
    proc.send(tx)
    r = eth.wait_for_receipt(tx.tx_hash)
    assert r


def test_aquire_estimate_gas_revert(proc, w3, rdp, tpool, wallet):
    tx = push_tx(w3, rdp, tpool, wallet, failed=True)
    with pytest.raises(EstimateGasRevertError):
        with proc.acquire_tx(tx):
            proc.process(tx)
    assert tx.tx_hash is None
    assert tx.status == TxStatus.SEEN
    assert tx.tx_id.encode('utf-8') in tpool.to_list()

    tx = push_ima_tx(w3, rdp, tpool, wallet, failed=True)

    with pytest.raises(EstimateGasRevertError):
        with proc.acquire_tx(tx):
            proc.process(tx)
    assert tx.tx_hash is None
    assert tx.status == TxStatus.DROPPED

    assert tx.tx_id.encode('utf-8') not in tpool.to_list()


def test_confirm(proc, w3, rdp, tpool, wallet):
    tx = push_tx(w3, rdp, tpool, wallet)
    proc.attempt_manager.make(tx)
    proc.send(tx)
    proc.wait(tx, max_time=proc.attempt_manager.current.wait_time)
    # Make sure it is confirmed after reasonable number of seconds
    with in_time(8):
        proc.confirm(tx)
    # Make sure next time it is confirmed instantly
    with in_time(0.1):
        proc.confirm(tx)
