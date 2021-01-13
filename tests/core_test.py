import mock

from skale.utils.web3_utils import get_receipt

from core import next_gas_price, sign_and_send, wait_for_receipt


def test_sign_and_send(web3, wallet):
    tx_data = {
        'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
        'value': 9,
        'gas': 200000,
        'gasPrice': web3.eth.gasPrice,
        'nonce': 7,
        'chainId': None,
        'data': '0x0'
    }
    tx_hash, error = sign_and_send(web3, wallet, tx_data)
    receipt = get_receipt(web3, tx_hash)
    assert receipt['status'] == 1
    assert isinstance(tx_hash, str)


def test_wait_for_receipt(web3):
    web3.eth.getTransactionReceipt = mock.Mock(side_effect=ValueError)
    tx_hash = '0x123'
    receipt = wait_for_receipt(web3, tx_hash, timeout=0.5, it_timeout=0.1)
    assert receipt is None
    assert web3.eth.getTransactionReceipt.call_count > 0


def test_next_gas_price():
    gas_price = 100
    assert next_gas_price(gas_price) == 113


def test_sign_and_send_wallet_error(web3, wallet):
    wallet.sign_and_send = mock.Mock(side_effect=ValueError('Test error'))
    tx_data = {
        'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
        'value': 9,
        'gas': 200000,
        'gasPrice': web3.eth.gasPrice,
        'nonce': 7,
        'chainId': None,
        'data': '0x0'
    }
    with mock.patch('core.get_max_gas_price',
                    mock.Mock(return_value=web3.eth.gasPrice * 1.1 * 1.1)):
        tx_hash, error = sign_and_send(web3, wallet, tx_data,
                                       max_iter=3,
                                       timeout=1, long_timeout=2)
        assert tx_hash is None
        assert error == 'Transaction was not sent'


@mock.patch('core.get_receipt', lambda *args: {})
def test_sign_and_send_wait_for_too_long(web3, wallet):
    tx_data = {
        'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
        'value': 9,
        'gas': 200000,
        'gasPrice': web3.eth.gasPrice,
        'nonce': 7,
        'chainId': None,
        'data': '0x0'
    }
    tx_hash, error = sign_and_send(web3, wallet, tx_data,
                                   max_iter=1,
                                   timeout=1, long_timeout=0)
    assert tx_hash is not None
    assert error == 'Fetching receipt failed: waiting limit exceded'


@mock.patch('core.get_receipt', lambda *args: None)
def test_sign_and_send_wait(web3, wallet):
    tx_data = {
        'to': '0x1057dc7277a319927D3eB43e05680B75a00eb5f4',
        'value': 9,
        'gas': 200000,
        'gasPrice': web3.eth.gasPrice,
        'nonce': 7,
        'chainId': None,
        'data': '0x0'
    }
    tx_hash, error = sign_and_send(web3, wallet, tx_data,
                                   max_iter=1,
                                   timeout=1, long_timeout=0)
    assert tx_hash is not None
    assert error == 'Failed to fetch receipt'
