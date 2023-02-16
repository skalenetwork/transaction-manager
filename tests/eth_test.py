import time

import pytest

from transaction_manager.eth import (
    BlockTimeoutError,
    MAX_WAITING_TIME,
    ReceiptTimeoutError,
)
from transaction_manager.structures import Tx, TxStatus

from tests.utils.account import send_eth
from tests.utils.timing import in_time


def test_eth_fee_history(eth):
    h = eth.get_fee_history()
    base_fee = eth.get_estimated_base_fee()
    tip = eth.get_p60_tip()
    assert isinstance(base_fee, int)
    assert isinstance(tip, int)
    assert base_fee > tip
    assert len(h['baseFeePerGas']) == 2
    assert len(h['reward'][0]) == 2


def test_eth_chain_id(eth):
    assert eth.chain_id == 31337


def test_eth_avg_gas_price(eth):
    assert 10 ** 9 < eth.avg_gas_price < 31 * 10 ** 9


def test_eth_blocks(w3, eth):
    assert 8000000 <= eth.block_gas_limit <= 100000000
    with in_time(seconds=MAX_WAITING_TIME):
        eth.wait_for_blocks(amount=1)
    with in_time(seconds=2):
        with pytest.raises(BlockTimeoutError):
            eth.wait_for_blocks(amount=10, max_time=0)


def test_eth_tx(w3wallet, w3, eth):
    acc = w3.eth.account.create()
    addr, pk = acc.address, acc.key.hex()
    assert eth.get_balance(addr) == 0
    send_eth(w3, w3wallet, addr, amount=10 ** 18)
    assert eth.get_balance(addr) == 10 ** 18
    assert eth.get_nonce(addr) == 0

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

    tx.gas = eth.calculate_gas(tx)
    assert tx.gas > 1.2 * 21000
    eth_tx_a = eth.convert_tx(tx)

    signed = w3.eth.account.sign_transaction(
        private_key=pk,
        transaction_dict=eth_tx_a
    )
    h = eth.send_tx(signed)
    with pytest.raises(ReceiptTimeoutError):
        eth.wait_for_receipt(h, max_time=0)

    time.sleep(1)
    eth_tx_a['gasPrice'] = 2 * eth.avg_gas_price
    second_nonce = w3.eth.get_transaction_count(addr)
    eth_tx_a['nonce'] = second_nonce
    signed = w3.eth.account.sign_transaction(eth_tx_a, private_key=pk)
    h = eth.send_tx(signed)
    status = eth.wait_for_receipt(h)
    assert status == 1
    assert eth.get_nonce(addr) == second_nonce + 1
    assert eth.get_tx_block(h) == eth.get_receipt(h)['blockNumber']


def test_eth_wait_for_blocks(eth, w3):
    eth.wait_for_blocks(amount=1, max_time=1)
    cblock = w3.eth.block_number
    eth.wait_for_blocks(amount=5, max_time=0, start_block=cblock - 10)
