import logging
import time
from typing import Dict

from skale.wallets import BaseWallet  # type: ignore

from .attempt import (
    aquire_attempt,
    Attempt,
    create_next_attempt,
    get_last_attempt,
    grad_inc_gas_price
)
from .config import CONFIRMATION_BLOCKS
from .eth import (
    Eth, is_replacement_underpriced, ReceiptTimeoutError
)
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
        tx.source = self.wallet.address
        tx.gas_price = gas_price
        tx.nonce = nonce
        tx.gas = self.eth.calculate_gas(tx.eth_tx)
        # IVD TODO: Handle sgx wallet failling
        for _ in range(3):
            logger.info(f'Signing transaction {tx.tx_id} {tx.eth_tx} ...')
            signed = self.wallet.sign(tx.eth_tx)
            try:
                # IVD TODO: Handle replacement underpriced error
                logger.info(f'Sending transaction {tx}')
                tx.tx_hash = self.eth.send_tx(signed)
            except Exception as err:
                logger.info(f'Sending failed with error {err}')
                if is_replacement_underpriced(err):
                    logger.info(
                        'Replacement gas price is too low. Trying to increase'
                    )
                    gas_price = grad_inc_gas_price(gas_price)
                else:
                    raise err
            else:
                break

        logger.info(f'Transaction {tx.tx_id} was sent successfully')
        tx.status = TxStatus.SENT
        tx.sent_ts = int(time.time())
        tx.attempts += 1

    def wait(self, tx: Tx, attempt: Attempt) -> Dict:
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
                    tx.status = TxStatus.DROPPED
                else:
                    tx.status = TxStatus.TIMEOUT
                return None
        if receipt:
            tx.set_as_completed(receipt)
            self.eth.wait_for_blocks(CONFIRMATION_BLOCKS)
            tx.status = TxStatus.CONFIRMED

    def handle(self, tx: Tx) -> None:
        # TODO: use tx.sent and fix mypy issues
        if tx.tx_hash is not None and (r := self.eth.get_receipt(tx.tx_hash)):
            logger.info(f'Tx {tx.tx_id} is already mined: {tx.tx_hash}')
            tx.set_as_completed(r)
            return
        else:
            logger.info(f'Configuring dynamic params for {tx.tx_id}')
            avg_gp = self.eth.avg_gas_price
            logger.info(f'Received avg gas pirce - {avg_gp}')
            nonce = self.eth.get_nonce(self.address)
            logger.info(f'Received current nonce - {nonce}')
            prev_attempt = get_last_attempt()
            attempt = create_next_attempt(
                nonce,
                avg_gp,
                tx.tx_id,
                prev_attempt
            )
            with aquire_attempt(attempt, tx) as attempt:
                self.send(tx, attempt.nonce, attempt.gas_price)
                self.wait(tx, attempt)

    def run(self) -> None:
        while True:
            try:
                if self.pool.size > 0:
                    with self.pool.aquire_next() as tx:
                        logger.info(f'Received transaction {tx}')
                        self.handle(tx)
            except Exception:
                logger.exception(
                    'Fetching next tx failed'
                )
            time.sleep(1)
