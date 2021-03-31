from unittest import mock

import pytest
from mock import Mock

from sgx.http import SgxUnreachableError
from skale.utils.web3_utils import wait_for_receipt_by_blocks
from skale.wallets.web3_wallet import generate_wallet

from core import sign_and_send, execute_dry_run, make_dry_run_call

TX_DICT = {
    'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
    'value': 9,
    'gas': 200000,
    'gasPrice': 1,
    'nonce': 7,
    'data': '0x0'
}


def test_sign_and_send(wallet, nonce_manager):
    tx, error = sign_and_send(TX_DICT, wallet, nonce_manager)
    assert error is None
    wait_for_receipt_by_blocks(
        wallet._web3,
        tx
    )
    assert isinstance(tx, str)


@pytest.fixture
def broken_wallet():
    bw_mock = Mock()
    bw_mock.sign_and_send = Mock(side_effect=ValueError('Nonce to low mock'))
    return bw_mock


def test_sign_and_send_broken_wallet(broken_wallet, nonce_manager):
    tx, error = sign_and_send(TX_DICT, broken_wallet, nonce_manager,
                              skip_dry_run=True)
    assert tx is None
    assert error == 'Nonce to low mock'
    assert broken_wallet.sign_and_send.call_count == 3


@pytest.fixture
def sgx_unreachable_wallet():
    sw_mock = Mock()
    sw_mock.sign_and_send = Mock(
        side_effect=SgxUnreachableError('sgx unreachable'))
    return sw_mock


def test_sign_and_send_sgx_broken_wallet(
        sgx_unreachable_wallet, nonce_manager):

    tx, error = sign_and_send(
        TX_DICT, sgx_unreachable_wallet,
        nonce_manager, skip_dry_run=True
    )
    assert tx is None
    assert error == 'Sgx server is unreachable'
    assert sgx_unreachable_wallet.sign_and_send.call_count == 1


def test_dry_run(nonce_manager, wallet):
    result, gas = execute_dry_run(nonce_manager.web3, wallet, TX_DICT)
    assert result == {'status': 1, 'gas': gas}
    assert gas == TX_DICT['gas']


def test_dry_run_failed(nonce_manager, wallet):
    failed_tx_dict = {
        'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
        'value': 10000000000,
        'gas': 200000,
        'gasPrice': 1,
        'nonce': 7
    }
    new_address = generate_wallet(nonce_manager.web3).address
    failed_tx_dict['from'] = new_address
    result, gas = execute_dry_run(nonce_manager.web3, wallet, failed_tx_dict)
    # Return status 1 on ganache
    assert result == {'status': 1, 'gas': gas}


def test_estimate_gas(nonce_manager, wallet):
    tx = TX_DICT.copy()
    del tx['gas']
    result, gas = execute_dry_run(nonce_manager.web3, wallet, tx)
    assert result == {'status': 1, 'gas': gas}
    assert isinstance(gas, int)
    assert gas > 0


def test_disable_dry_run_env(nonce_manager, wallet, disable_dry_run_env):
    with mock.patch('core.execute_dry_run') as dry_run_mock:
        tx, error = sign_and_send(TX_DICT, wallet, nonce_manager)
        dry_run_mock.assert_not_called()
        assert error is None
        wait_for_receipt_by_blocks(
            wallet._web3,
            tx
        )
        assert isinstance(tx, str)


def test_skip_dry_run(nonce_manager, wallet):
    with mock.patch('core.execute_dry_run') as dry_run_mock:
        tx, error = sign_and_send(
            TX_DICT, wallet, nonce_manager, skip_dry_run=True)
        dry_run_mock.assert_not_called()
        assert error is None
        wait_for_receipt_by_blocks(
            wallet._web3,
            tx
        )
        assert isinstance(tx, str)


def test_make_dry_run_call(nonce_manager, wallet):
    modified_gas_tx_dict = TX_DICT.copy()
    modified_gas_tx_dict['gas'] = 200000
    dry_run_result = make_dry_run_call(nonce_manager.web3, wallet, TX_DICT)
    # Check that gas was restimated
    assert dry_run_result['status'] == 1
    assert dry_run_result['gas'] != modified_gas_tx_dict['gas']
