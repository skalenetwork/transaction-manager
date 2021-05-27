import logging
from .eth import Eth
from .processor import Processor
from .txpool import TxPool
from .wallet import init_wallet
from .log import init_logger

logger = logging.getLogger(__name__)


def main() -> None:
    init_logger()
    eth = Eth()
    pool = TxPool()
    wallet = init_wallet()
    proc = Processor(eth, pool, wallet)
    proc.run()


if __name__ == '__main__':
    main()
