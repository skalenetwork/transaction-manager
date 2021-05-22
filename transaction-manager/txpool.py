""" Process transaction messages from queue """

from .radapter import RedisAdapter


class TxPool:
    def __init__(self) -> None:
        self.rs = RedisAdapter()

    def get_next():
        pass

    def aquire():
        pass

    def release():
        pass
