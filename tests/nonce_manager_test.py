from skale.utils.web3_utils import get_eth_nonce


def test_increment(nonce_manager):
    nonce_before = nonce_manager.ensure_nonce()
    assert nonce_before == nonce_manager._nonce
    nonce_manager.increment()
    nonce_after = nonce_manager.ensure_nonce()
    assert nonce_after == nonce_manager._nonce
    assert nonce_after == nonce_before + 1


def test_increment_with_sending_tx(nonce_manager):
    # Send tx without nonce updating
    nonce_manager.healthcheck()
    nonce_manager.healthcheck()

    # Incrementing using local nonce
    nonce_manager.increment()
    eth_nonce = get_eth_nonce(nonce_manager.skale.web3,
                              nonce_manager.skale.wallet.address)
    assert nonce_manager._nonce == eth_nonce + 1


def test_increment_with_request_network_nonce(nonce_manager):
    nonce_manager.healthcheck()
    nonce_manager.healthcheck()
    # Incrementing with requesting network_nonce
    nonce_manager.increment(request_from_network=True)
    eth_nonce = get_eth_nonce(nonce_manager.skale.web3,
                              nonce_manager.skale.wallet.address)
    assert nonce_manager._nonce == eth_nonce + 1


def test_fix_nonce(nonce_manager):
    initial_nonce = nonce_manager.ensure_nonce()
    nonce_manager._nonce = initial_nonce - 1
    nonce_manager.fix_nonce()
    assert nonce_manager._nonce == initial_nonce
