import json

import mock
import pytest

from transaction_manager.config import MAX_RESUBMIT_AMOUNT
from transaction_manager.processor import Processor, SendingError
from transaction_manager.structures import TxStatus

from tests.utils.account import generate_address


@pytest.fixture
def proc(tpool, eth, trs, w3wallet):
    return Processor(eth, tpool, w3wallet)


def make_tx(rdp, tpool, to: str, value: int = 10):
    eth_tx = {
        'from': rdp.address,
        'to': to,
        'value': 10
    }
    tx_id = rdp.sign_and_send(eth_tx)
    raw_id = tx_id.encode('utf-8')
    return tpool.get(raw_id)


def get_from_pool(tx_id, tpool):
    raw_id = tx_id.encode('utf-8')
    return tpool.get(raw_id)


class ProcTestError(Exception):
    pass


def test_processor_acquire_tx(proc, tpool, eth, trs, w3, w3wallet, rdp):
    to_a = generate_address(w3)
    tx = make_tx(rdp, tpool, to_a)
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


def test_get_exec_data(proc, w3, rdp, eth, tpool):
    to_a = generate_address(w3)
    tx = make_tx(rdp, tpool, to_a)
    tx.hashes = ['0x1234', '0x1235', '0x12346']
    tx.attempts = 3
    eth.get_status = mock.Mock(return_value=-1)
    h, r = proc.get_exec_data(tx)
    assert r is None and h is None

    eth.get_status = mock.Mock(return_value=1)
    h, r = proc.get_exec_data(tx)
    assert r == 1 and h == '0x12346'


def test_send(proc, w3, rdp, eth, tpool):
    to_a = generate_address(w3)
    tx = make_tx(rdp, tpool, to_a)
    tx.gas = 22000
    tx.gas_price = 10 ** 9

    proc.eth.send_tx = mock.Mock(
        side_effect=ValueError({
                'code': -32000,
                'message': 'replacement transaction underpriced'
            })
    )
    with pytest.raises(SendingError):
        proc.send(tx)
    assert tx.tx_hash is None
    assert tx.hashes == []

    proc.eth.send_tx = mock.Mock(
        side_effect=ValueError('unknown error')
    )
    with pytest.raises(SendingError):
        proc.send(tx)
    assert tx.tx_hash is None
    assert tx.hashes == []

    proc.eth.send_tx = mock.Mock(return_value='0x12323213213321321')
    proc.send(tx)
    assert tx.tx_hash == '0x12323213213321321'
    assert tx.hashes == ['0x12323213213321321']

    proc.eth.send_tx = mock.Mock(return_value='0x213812903813123')
    proc.send(tx)
    assert tx.tx_hash == '0x213812903813123'
    assert tx.hashes == ['0x12323213213321321', '0x213812903813123']


@pytest.mark.skip
def test_processor(tpool, eth, trs, w3wallet, rdp):
    eth_tx_a = {
        'from': rdp.address,
        'to': rdp.address,
        'value': 10,
        'gasPrice': 1,
        'gas': 22000,
        'nonce': 0
    }
    tx_id = rdp.sign_and_send(eth_tx_a)
    tx = rdp.wait(tx_id, timeout=2)
    assert tx['status'] == 'SUCCESS'
    assert tx['from'] == rdp.address
    assert tx['to'] == rdp.address
    assert tx['nonce'] == eth.get_nonce(rdp.address) - 1
    last_attempt = json.loads(trs.get(b'last_attempt').decode('utf-8'))
    assert tx['nonce'] == last_attempt['nonce']
    assert tx['attempts'] == last_attempt['index']
    assert tx['gasPrice'] == last_attempt['fee']['gas_price']
    assert tx['data'] is None
    assert tx['score'] == 1
    assert tx_id == last_attempt['tx_id']
