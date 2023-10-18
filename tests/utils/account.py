import os
from eth_typing.evm import ChecksumAddress
from skale.wallets import BaseWallet  # type: ignore
from web3 import Web3


SKALE_DIR = os.getenv('SKALE_DIR')
HOST_CONFIG_PATH = os.path.join(SKALE_DIR, 'node_data', 'node_config.json')
CERT_DIR = os.path.join(SKALE_DIR, 'node_data', 'sgx_certs')


def send_eth(
    w3: Web3,
    wallet: BaseWallet,
    address: ChecksumAddress,
    amount: int
) -> None:
    tx = {
        'to': address,
        'value': amount,
        'gas': 8000000,
        'gasPrice': w3.eth.gas_price
    }
    signed_txn = wallet.sign(tx)
    h = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
    w3.eth.wait_for_transaction_receipt(h, timeout=60)


def generate_address(w3: Web3) -> str:
    return w3.eth.account.create().address
