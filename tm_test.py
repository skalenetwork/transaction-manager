import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor as Executor, as_completed

from sgx import SgxClient

from skale import Skale
from skale.utils.account_tools import send_ether
from skale.utils.web3_utils import init_web3
from skale.wallets import RPCWallet, Web3Wallet


MAX_WORKERS = int(os.getenv('MAX_WORKERS'))
TRANSACTION_AMOUNT = int(os.getenv('TRANSACTION_AMOUNT'))
ENDPOINT = os.getenv('ENDPOINT')
TEST_ABI_FILEPATH = os.getenv('TEST_ABI_FILEPATH')
SGX_SERVER_URL = os.getenv('SGX_SERVER_URL')
SGX_CERTS_FOLDER = os.getenv('SGX_CERTS_FOLDER')
KEYNAME_FILEPATH = os.getenv('KEYNAME_FILEPATH')
ETH_PRIVATE_KEY = os.getenv('ETH_PRIVATE_KEY')


logger = logging.getLogger(__name__)


def init_logger():
    logging.basicConfig(level=logging.ERROR)


init_logger()


def init_base_wallet():
    web3 = init_web3(ENDPOINT)
    return Web3Wallet(ETH_PRIVATE_KEY, web3)


base_wallet = init_base_wallet()


def get_keyname():
    if not os.path.isfile(KEYNAME_FILEPATH):
        return None
    with open(KEYNAME_FILEPATH) as keyname_file:
        return json.load(keyname_file)['sgx_key_name']


def save_keyname(keyname):
    with open(KEYNAME_FILEPATH, 'w') as keyname_file:
        return json.dump({'sgx_key_name': keyname}, keyname_file)


def run_simple_tx(skale, tx_id, mda,
                  gas_price=None, skip_dry_run=False):
    return tx_id, skale.validator_service.set_validator_mda(
        mda, gas_price=gas_price, skip_dry_run=skip_dry_run
    )


def init_validator(skale):
    amount = 0.1
    print(f'Sending {amount} ETH to validator account')
    send_ether(skale.web3, base_wallet, skale.wallet.address, amount)

    print(f'Registering new validator. Address: {skale.wallet.address}')
    validator_name = 'test'
    description = 'test'
    fee_rate = 1
    initial_mda = 1
    skale.validator_service.register_validator(
        validator_name, description, fee_rate, initial_mda)


def run_txs(skale):
    address = skale.wallet.address
    if not skale.validator_service.validator_address_exists(address):
        init_validator(skale)
    print('Running test ...')
    mda = 2
    with Executor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(run_simple_tx, skale, tx_id, mda,
                            gas_price=skale.web3.eth.gasPrice // (2 ** tx_id),
                            skip_dry_run=False)
            for tx_id in range(TRANSACTION_AMOUNT)
        ]
        results = []
        for future in as_completed(futures):
            tx_id, res = future.result()
            results.append(res.receipt['status'] == 1)
            print(f'Completed: {tx_id} status {res.receipt["status"]}')
        assert all(results)


def init_skale(endpoint, wallet, test_abi_filepath):
    return Skale(endpoint, test_abi_filepath, wallet)


def init_sgx_key(sgx_server_url, sgx_certs_dir):
    sgx = SgxClient(sgx_server_url, sgx_certs_dir)
    key_info = sgx.generate_key()
    save_keyname(key_info.name)
    return key_info.name


def init_wallet(sgx_server_url,
                endpoint=ENDPOINT, sgx_certs_dir=SGX_CERTS_FOLDER):
    keyname = get_keyname()
    if not keyname:
        keyname = init_sgx_key(sgx_server_url, sgx_certs_dir=sgx_certs_dir)
    web3 = init_web3(endpoint)
    return RPCWallet(
        url='http://127.0.0.1:3008',
        web3=web3,
        sgx_endpoint=sgx_server_url,
        key_name=keyname,
        path_to_cert=sgx_certs_dir,
        retry_if_failed=True
    )


def main():
    print(ENDPOINT)
    wallet = init_wallet(SGX_SERVER_URL)
    print(f'Wallet address: {wallet.address}')
    skale = init_skale(ENDPOINT, wallet, TEST_ABI_FILEPATH)
    print('Skale inited. Running transactions ...')
    run_txs(skale)


if __name__ == '__main__':
    main()
