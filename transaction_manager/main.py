import logging
from transaction_manager.eth import Eth
from transaction_manager.processor import Processor
from transaction_manager.txpool import TxPool
from transaction_manager.wallet import init_wallet

logger = logging.getLogger(__name__)


def main() -> None:
    eth = Eth()
    pool = TxPool()
    wallet = init_wallet()
    proc = Processor(eth, pool, wallet)
    proc.run()


if __name__ == '__main__':
    main()
