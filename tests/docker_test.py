import json
import time
from concurrent.futures import as_completed, ThreadPoolExecutor
from functools import wraps

import pytest
from skale.wallets import RedisWalletAdapter

from tests.utils.contracts import get_tester_abi


DEFAULT_GAS = 21000
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
                return func(*args, *kwargs)
            except Exception as e:
                err = e
                time.sleep(2)
        raise err
    return wrapper


@retry_rdp
def make_simple_tx(w3, rdp, w3wallet, failed=False):
    tester_abi = get_tester_abi()
    tester = w3.eth.contract(
        abi=tester_abi['abi'],
        address=tester_abi['address']
    )
    number = 3 if failed else 4
    set_only_even_tx = tester.functions.setOnlyEven(
        number
    ).buildTransaction({
        'gasPrice': w3.eth.gasPrice,
        'gas': DEFAULT_GAS,
        'from': w3wallet.address
    })
    return rdp.sign_and_send(set_only_even_tx, priority=6)


@retry_rdp
def wait_for_tx(rdp, tx_id):
    rdp.wait(tx_id, timeout=300)
    return rdp.get_record(tx_id)


def test_processor(tpool, w3, eth, trs, rdp, wallet):
    tester_abi = get_tester_abi()
    tx_id = make_simple_tx(w3, rdp, wallet)
    rec = rdp.wait(tx_id, timeout=60)
    assert rec['status'] == 1
    tx = rdp.get_record(tx_id)
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
    assert tx_id == last_attempt['tx_id']


def test_processor_many_tx(tpool, eth, w3, trs, rdp):
    addrs = [w3.eth.account.create().address for i in range(TX_NUMBER)]
    futures = []
    with ThreadPoolExecutor(max_workers=3) as p:
        futures = [p.submit(make_simple_tx, rdp, addr) for addr in addrs]

    tids = [f.result() for f in as_completed(futures)]

    with ThreadPoolExecutor(max_workers=3) as p:
        futures = [p.submit(wait_for_tx, rdp, tid) for tid in tids]
    txs = [f.result() for f in as_completed(futures)]
    assert any(tx['status'] == 'SUCCESS' for tx in txs)
    assert tpool.size == 0
