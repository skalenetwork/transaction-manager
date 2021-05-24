import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, Optional


class TxStatus(Enum):
    PROPOSED = 1
    PENDING = 2
    SUCCESS = 3
    FAILED = 4
    TIMEOUT = 5


@dataclass
class Tx:
    tx_id: str
    status: TxStatus
    priority: int
    to: str
    value: int
    gas: Optional[int] = None
    gas_price: Optional[int] = None
    nonce: Optional[int] = None
    data: Optional[Dict] = None
    tx_hash: Optional[str] = None
    receipt: Optional[Dict] = None

    @property
    def raw_id(self) -> bytes:
        return self.tx_id.encode('utf-8')

    def is_completed(self) -> bool:
        return self.status in (
            TxStatus.SUCCESS,
            TxStatus.FAILED,
            TxStatus.TIMEOUT
        )

    @property
    def eth_tx(self) -> Dict:
        return {
            'to': self.to,
            'value': self.value,
            'gas': self.gas,
            'gasPrice': self.gas_price,
            'nonce': self.nonce,
            'data': self.data
        }

    def to_bytes(self) -> bytes:
        plain_tx = asdict(self)
        del plain_tx['tx_id']
        del plain_tx['gas_price']
        plain_tx['status'] = self.status.name
        plain_tx['gasPrice'] = self.gas_price
        return json.dumps(plain_tx).encode('utf-8')

    @classmethod
    def from_bytes(cls, tx_id: bytes, tx_bytes: bytes) -> 'Tx':
        plain_tx = json.loads(tx_bytes.decode('utf-8'))
        plain_tx['status'] = TxStatus[plain_tx['status']]
        plain_tx['gas_price'] = plain_tx.get('gasPrice')
        if 'gasPrice' in plain_tx:
            del plain_tx['gasPrice']
        plain_tx['tx_hash'] = plain_tx.get('hash')
        if 'hash' in plain_tx:
            del plain_tx['hash']
        return Tx(tx_id=tx_id.decode('utf-8'), **plain_tx)
