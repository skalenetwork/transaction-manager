import json
import logging

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TxStatus(Enum):
    PROPOSED = 1
    SENT = 2
    TIMEOUT = 3
    DROPPED = 4
    SUCCESS = 5
    FAILED = 6
    CONFIRMED = 7


@dataclass
class Tx:
    tx_id: str
    status: TxStatus
    priority: int
    to: str
    value: int
    source: Optional[str] = None
    gas: Optional[int] = None
    chain_id: Optional[int] = None
    gas_price: Optional[int] = None
    nonce: Optional[int] = None
    data: Optional[Dict] = None
    tx_hash: Optional[str] = None
    attempts: int = 0
    sent_ts: Optional[int] = None

    @property
    def raw_id(self) -> bytes:
        return self.tx_id.encode('utf-8')

    def is_completed(self) -> bool:
        return self.status in (
            TxStatus.SUCCESS,
            TxStatus.FAILED,
            TxStatus.DROPPED
        )

    def is_sent(self) -> bool:
        return self.tx_hash is not None

    def set_as_completed(self, receipt: Dict) -> None:
        if receipt['status'] == 1:
            s = TxStatus.SUCCESS
        else:
            s = TxStatus.FAILED
        self.status = s
        self.receipt = receipt

    @property
    def eth_tx(self) -> Dict:
        etx: Dict = {
            'from': self.source,
            'to': self.to,
            'value': self.value,
            'gasPrice': self.gas_price,
            'nonce': self.nonce,
            'chainId': self.chain_id,
        }
        if self.gas:
            etx.update({'gas': self.gas})
        if self.data:
            etx.update({'data': self.data})
        return etx

    def to_bytes(self) -> bytes:
        plain_tx = asdict(self)
        del plain_tx['tx_id']
        del plain_tx['gas_price']
        del plain_tx['source']
        plain_tx['status'] = self.status.name
        plain_tx['gasPrice'] = self.gas_price
        plain_tx['from'] = self.source

        return json.dumps(plain_tx, sort_keys=True).encode('utf-8')

    @classmethod
    def from_bytes(cls, tx_id: bytes, tx_bytes: bytes) -> 'Tx':
        logger.debug(f'Transaction tx_bytes {tx_bytes}')
        plain_tx = json.loads(tx_bytes.decode('utf-8'))
        plain_tx['status'] = TxStatus[plain_tx['status']]
        plain_tx['gas_price'] = plain_tx.get('gasPrice')
        plain_tx['source'] = plain_tx.get('from')
        if 'gasPrice' in plain_tx:
            del plain_tx['gasPrice']
        if 'from' in plain_tx:
            del plain_tx['from']
        return Tx(tx_id=tx_id.decode('utf-8'), **plain_tx)
