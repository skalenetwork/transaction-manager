import json
import pytest

from transaction_manager.processor import Processor
from transaction_manager.transaction import TxStatus

from tests.utils.account import generate_address


@pytest.fixture
def proc(tpool, eth, trs, w3wallet):
    return Processor(eth, tpool, w3wallet)


def make_tx(rdp, to: str, value: int = 10):
    eth_tx = {
        'from': rdp.address,
        'to': to,
        'value': 10
    }
    return rdp.sign_and_send(eth_tx)


class ProcTestError(Exception):
    pass


def test_processor_aquire(proc, tpool, eth, trs, w3, w3wallet, rdp):
    to_a = generate_address(w3)
    tx_id = make_tx(rdp, to_a)
    raw_id = tx_id.encode('utf-8')
    tx = tpool.get(raw_id)
    with proc.aquire_tx(tx):
        tx.status = TxStatus.SUCCESS
    assert tpool.get(raw_id).status == TxStatus.SUCCESS

    try:
        with proc.aquire_tx(tx):
            tx.status = TxStatus.SENT
            raise ProcTestError('Test error')
    except ProcTestError:
        assert tpool.get(raw_id).status == TxStatus.SENT


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
    assert tx['gasPrice'] == last_attempt['gas_price']
    assert tx['data'] is None
    assert tx['score'] == 1
    assert tx_id == last_attempt['tx_id']
