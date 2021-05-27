from eth_typing.evm import ChecksumAddress
from skale.wallets import BaseWallet  # type: ignore
from web3 import Web3


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
        'gasPrice': w3.eth.gasPrice
    }
    signed_txn = wallet.sign(tx)
    h = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
    w3.eth.waitForTransactionReceipt(h, timeout=60)
