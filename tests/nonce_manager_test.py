def test_increment(nonce_manager):
    nonce_before = nonce_manager.ensure_nonce()
    assert nonce_before == nonce_manager._nonce
    nonce_manager.increment()
    nonce_after = nonce_manager.ensure_nonce()
    assert nonce_after == nonce_manager._nonce
    assert nonce_after == nonce_before + 1


def test_fix_nonce(nonce_manager):
    initial_nonce = nonce_manager.ensure_nonce()
    nonce_manager._nonce = initial_nonce - 1
    nonce_manager.fix_nonce()
    assert nonce_manager._nonce == initial_nonce
