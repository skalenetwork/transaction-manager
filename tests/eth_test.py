import pytest

from transaction_manager.eth import (
    BlockTimeoutError,
    MAX_WAITING_TIME,
    ReceiptTimeoutError,
)

from tests.utils.account import send_eth
from tests.utils.timing import in_time


def test_eth_chain_id(eth):
    assert 100 < eth.chain_id < 200


def test_eth_avg_gas_price(eth):
    assert eth.avg_gas_price == 10 ** 9


def test_eth_blocks(w3, eth):
    assert 800000 <= eth.block_gas_limit <= 10000000
    with in_time(seconds=MAX_WAITING_TIME):
        eth.wait_for_blocks(amount=1)
    with in_time(seconds=2):
        with pytest.raises(BlockTimeoutError):
            eth.wait_for_blocks(amount=10, max_time=1)


def test_eth_tx(w3wallet, w3, eth):
    acc = w3.eth.account.create()
    addr, pk = acc.address, acc.key.hex()
    assert eth.get_balance(addr) == 0
    send_eth(w3, w3wallet, addr, amount=10 ** 18)
    assert eth.get_balance(addr) == 10 ** 18
    assert eth.get_nonce(addr) == 0

    eth_tx_a = {
        'from': addr,
        'to': addr,
        'value': 1,
        'gasPrice': 1,
        'gas': 22000,
        'nonce': 0,
        'chainId': w3.eth.chainId
    }
    # TODO: IVD WHY 8000000 ?
    assert eth.calculate_gas(eth_tx_a) == 8000000

    signed = w3.eth.account.sign_transaction(eth_tx_a, private_key=pk)
    h = eth.send_tx(signed)
    with pytest.raises(ReceiptTimeoutError):
        eth.wait_for_receipt(h, max_time=1)

    eth_tx_a['gasPrice'] = 2 * eth.avg_gas_price
    signed = w3.eth.account.sign_transaction(eth_tx_a, private_key=pk)
    h = eth.send_tx(signed)
    receipt = eth.wait_for_receipt(h)
    assert receipt['status'] == 1
    assert eth.get_nonce(addr) == 1
