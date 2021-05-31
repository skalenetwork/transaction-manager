import logging
# import time

from .eth import Eth
from .log import init_logger
# from .node import is_config_created
from .processor import Processor
from .txpool import TxPool
from .wallet import init_wallet

logger = logging.getLogger(__name__)


def main() -> None:
    init_logger()

    # while not is_config_created():
    #     logger.info('Waiting for node config generation ...')
    #     time.sleep(2)

    logger.info('Initializing transaction manager ...')
    eth = Eth()
    pool = TxPool()
    wallet = init_wallet()
    proc = Processor(eth, pool, wallet)
    logger.info('Starting transaction processor ...')
    proc.run()


if __name__ == '__main__':
    main()
