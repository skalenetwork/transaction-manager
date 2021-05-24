import binascii
import json
import os
import time
from threading import Thread
from typing import Dict, Tuple

from redis import Redis


class Web3Sender:
    pass


class RedisSender:
    ID_SIZE = 16

    def __init__(self, rclient: Redis, pool: str) -> None:
        self.rs = rclient
        self.pool = pool

    @classmethod
    def _make_raw_id(cls) -> bytes:
        return b'tx-' + binascii.b2a_hex(os.urandom(cls.ID_SIZE))

    @classmethod
    def _make_record(cls, tx: Dict, priority: int) -> Tuple[bytes, bytes]:
        tx_id = cls._make_raw_id()
        record = json.dumps({
            'status': 'PROPOSED',
            'priority': priority,
            'hash': None,
            'receipt': None,
            **tx
        }).encode('utf-8')
        return tx_id, record

    @classmethod
    def _to_raw_id(cls, tx_id: str) -> bytes:
        return tx_id.encode('utf-8')

    def _to_id(cls, raw_id: str) -> str:
        return raw_id.decode('utf-8')

    def send(self, tx: Dict, priority: int = 1) -> str:
        raw_id, tx_record = self._make_record(tx, priority)
        pipe = self.rs.pipeline()
        pipe.zadd(self.pool, {raw_id: priority})
        pipe.set(raw_id, tx_record)
        pipe.execute()
        return self._to_id(raw_id)

    def get_status(self, tx_id: str) -> str:
        return self.get_record(tx_id)['status']

    def get_record(self, tx_id: str) -> Dict:
        rid = self._to_raw_id(tx_id)
        return json.loads(self.rs.get(rid).decode('utf-8'))

    def wait(self, tx_id: str, timeout: int = 5) -> str:
        start_ts = time.time()
        while time.time() - start_ts < timeout:
            status = self.get_status(tx_id)
            if status == 'Mined' or status == 'Lost':
                return 'Finished'
        raise TimeoutError(f'Transaction has not been mined within {timeout}')


def mining(sender: RedisSender, tx: Dict) -> None:
    def mine_transaction():
        time.sleep(10)
        sender.rs.set(tx, json.dumps({'status': 'Mined'}).encode('utf-8'))
    t = Thread(target=mine_transaction)
    t.start()
    t.join()


def main() -> None:
    r = Redis(host='127.0.0.1')
    sender = RedisSender(r, 'tx_pool')
    tx_data = {
        'to': '0x1',
        'value': 10,
        'gasPrice': 1,
        'gas': 22000,
        'nonce': 0
    }
    msg_id = sender.send(tx_data)
    status = sender.get_status(msg_id)
    print(status)
    sender.wait(msg_id)
    status = sender.get_status(msg_id)
    print(status)


if __name__ == '__main__':
    main()
