import logging
import time

from skale.wallets import BaseWallet  # type: ignore

from .attempt import (
    aquire_attempt,
    create_next_attempt,
    get_last_attempt,
    grad_inc_gas_price
)
from .eth import Eth, is_replacement_underpriced, ReceiptTimeoutError
from .transaction import Tx, TxStatus
from .txpool import TxPool

logger = logging.getLogger(__name__)


class Processor:
    def __init__(self, eth: Eth, pool: TxPool, wallet: BaseWallet) -> None:
        self.eth: Eth = eth
        self.pool: TxPool = pool
        self.wallet: BaseWallet = wallet
        self.address = wallet.address

    def send(self, tx: Tx, nonce: int, gas_price: int) -> None:
        tx.chain_id = self.eth.chain_id
        tx.gas_price = gas_price
        tx.nonce = nonce
        tx.gas = self.eth.calculate_gas(tx.eth_tx)
        # IVD TODO: Handle sgx wallet failling
        for _ in range(3):
            try:
                signed = self.wallet.sign(tx.eth_tx)
                # IVD TODO: Handle replacement underpriced error
                tx.tx_hash = self.eth.send_tx(signed)
            except ValueError as err:
                if is_replacement_underpriced(err):
                    gas_price = grad_inc_gas_price(gas_price)

        tx.sent_ts = time.time()
        tx.attempts += 1

    def handle(self, tx: Tx) -> None:
        # TODO: use tx.sent and fix mypy issues
        if tx.tx_hash is not None and (r := self.eth.get_receipt(tx.tx_hash)):
            logger.info(f'Tx {tx.tx_id} is already mined: {tx.tx_hash}')
            tx.set_as_completed(r)
            return
        else:
            avg_gp = self.eth.avg_gas_price
            nonce = self.eth.get_nonce(self.address)
            prev_attempt = get_last_attempt()
            attempt = create_next_attempt(
                nonce,
                avg_gp,
                tx.tx_id,
                prev_attempt
            )

            with aquire_attempt(attempt, tx):
                print('Aquiring attempt')
                self.send(tx, attempt.nonce, attempt.gas_price)

            max_time = attempt.wait_time

            receipt = None
            if tx.tx_hash:
                try:
                    receipt = self.eth.wait_for_receipt(
                        tx_hash=tx.tx_hash,
                        max_time=max_time
                    )
                except ReceiptTimeoutError:
                    logger.info(f'{tx.tx_id} is not mined within {max_time}')
                    if attempt.is_last():
                        tx.status = TxStatus.NOT_SENT
                    return
        if receipt:
            tx.set_as_completed(receipt)

    def run(self) -> None:
        while True:
            if self.pool.size > 0:
                with self.pool.aquire_next() as tx:
                    self.handle(tx)
            time.sleep(1)
