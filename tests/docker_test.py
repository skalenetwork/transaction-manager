import json
import random
import time
from concurrent.futures import as_completed, ThreadPoolExecutor
from functools import wraps

import pytest
from skale.transactions.exceptions import TransactionNotMinedError
from skale.wallets import RedisWalletAdapter

from transaction_manager.config import (
    HARD_REPLACE_TIP_OFFSET,
    TARGET_REWARD_PERCENTILE
)
from transaction_manager.structures import TxStatus
from tests.utils.contracts import get_tester_abi


DEFAULT_GAS = 20000
TX_NUMBER = 10
RETRY_NUMBER = 10


@pytest.fixture
def rdp(trs, w3wallet):
    """ Redis wallet for docker based tests """
    return RedisWalletAdapter(trs, 'transactions', w3wallet)


def retry_rdp(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        err = None
        for i in range(RETRY_NUMBER):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                err = e
                time.sleep(2)
        raise err
    return wrapper


@retry_rdp
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
    tx_id = rdp.sign_and_send(tx, priority=6)
    raw_id = tx_id.encode('utf-8')
    return tpool.get(raw_id)


def push_simple_tx(rdp, address):
    etx = {'to': address, 'value': 10}
    return rdp.sign_and_send(etx)


@retry_rdp
def wait_for_tx(rdp, tx_id):
    rdp.wait(tx_id, timeout=300)
    return rdp.get_record(tx_id)


def test_processor(tpool, w3, eth, trs, rdp, wallet):
    tester_abi = get_tester_abi()
    tx_obj = push_tx(w3, rdp, tpool, wallet)
    rec = rdp.wait(tx_obj.tx_id, timeout=60)
    assert rec['status'] == 1
    tx = rdp.get_record(tx_obj.tx_id)
    assert tx['status'] == 'SUCCESS'
    assert tx['from'] == wallet.address
    assert tx['to'] == tester_abi['address']
    assert tx['nonce'] == eth.get_nonce(wallet.address) - 1
    last_attempt = json.loads(trs.get(b'last_attempt').decode('utf-8'))
    assert tx['nonce'] == last_attempt['nonce']
    assert tx['attempts'] == last_attempt['index']
    assert tx['gasPrice'] == last_attempt['fee']['gas_price']
    assert tx['data'] == '0x8e4ed53e0000000000000000000000000000000000000000000000000000000000000004'  # noqa
    assert tx['score'] > 6 * 10 ** 10 + int(time.time() - 10)
    assert tx['tx_id'] == last_attempt['tx_id']


def test_processor_many_tx(tpool, eth, w3, trs, rdp):
    addrs = [w3.eth.account.create().address for i in range(TX_NUMBER)]
    futures = []
    with ThreadPoolExecutor(max_workers=3) as p:
        futures = [p.submit(push_simple_tx, rdp, addr) for addr in addrs]

    tids = [f.result() for f in as_completed(futures)]

    with ThreadPoolExecutor(max_workers=3) as p:
        futures = [p.submit(wait_for_tx, rdp, tid) for tid in tids]
    txs = [f.result() for f in as_completed(futures)]
    assert any(tx['status'] == 'SUCCESS' for tx in txs)
    assert tpool.size == 0


@pytest.mark.skip('Geth only')
def test_replace_legacy(eth, w3, rdp, tpool, wallet):
    # First transaction is legacy that meant to stuck
    raw_tx = make_tx(w3, wallet)
    history = w3.eth.fee_history(
        1,
        'latest',
        # Switch to bigger percentile to make sure it cannot be easily replaced
        [50, TARGET_REWARD_PERCENTILE + 10]
    )
    # Setting cap as tip to make it stuck
    raw_tx['gasPrice'] = max(
        history['baseFeePerGas'][-1],
        history['reward'][0][-1] * 5
    )
    # To prevent already known error
    raw_tx['gas'] = 30000 + random.randint(0, 3000)
    raw_tx['nonce'] = eth.get_nonce(wallet.address)
    stuck_tx_hash = wallet.sign_and_send(raw_tx)

    tx_id = rdp.sign_and_send(raw_tx)
    rdp.wait(tx_id)
    raw_id = tx_id.encode('utf-8')
    tx = tpool.get(raw_id)
    assert tx.fee.max_fee_per_gas == tx.fee.max_priority_fee_per_gas + HARD_REPLACE_TIP_OFFSET
    assert tx.tx_hash is not None
    assert tx.status == TxStatus.SUCCESS

    with pytest.raises(TransactionNotMinedError):
        wallet.wait(stuck_tx_hash, timeout=5)

    # Ensure that next tx is sent in a regular way
    tx_id = rdp.sign_and_send(raw_tx)
    rdp.wait(tx_id)
    raw_id = tx_id.encode('utf-8')
    tx = tpool.get(raw_id)
    assert tx.tx_hash is not None
    assert tx.status == TxStatus.SUCCESS
    assert tx.fee.max_priority_fee_per_gas + HARD_REPLACE_TIP_OFFSET < tx.fee.max_fee_per_gas
