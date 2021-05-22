import dataclasses
import json
from enum import Enum
from typing import Dict


class TxStatus(Enum):
    PROPOSED = 1
    PENDING = 2
    SUCCESS = 3
    FAILED = 4
    TIMEOUT = 5


@dataclasses.dataclass
class Tx:
    tx_id: str
    status: TxStatus
    priority: int
    to: str
    value: int
    gas: int
    gas_price: int
    nonce: int
    data: Dict
    tx_hash: str = None
    receipt: Dict = None

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
        plain_tx = dataclasses.asdict(self)
        del plain_tx['tx_id']
        del plain_tx['gas_price']
        plain_tx['status'] = self.status.name
        plain_tx['gasPrice'] = self.gas_price
        return json.dumps(plain_tx).encode('utf-8')

    @classmethod
    def from_bytes(cls, tx_id: bytes, tx_bytes: bytes) -> 'Tx':
        plain_tx = json.loads(tx_bytes.decode('utf-8'))
        plain_tx['status'] = TxStatus[plain_tx['status']]
        plain_tx['gas_price'] = plain_tx['gasPrice']
        del plain_tx['gasPrice']
        return Tx(tx_id=tx_id.decode('utf-8'), **plain_tx)
