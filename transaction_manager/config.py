import os
import sys
from typing import Optional

REDIS_URI: str = 'redis://@127.0.0.1:6379'

SGX_URL: Optional[str] = 'http://127.0.0.1:1026'

ETH_PRIVATE_KEY: Optional[str] = None

ENDPOINT: str = 'http://127.0.0.1:1919'

GAS_MULTIPLIER: float = 1.8


for v in list(
    filter(
        lambda v: not v.startswith('__') and v in os.environ,
        globals()
    )
):
    type_ = type(getattr(sys.modules[__name__], v))
    if not isinstance(None, type_):
        casted = type_(os.environ[v])
    else:
        globals()[v] = os.environ[v]
