""" Configuration params """
import os
import sys

REDIS_URI = 'redis://@127.0.0.1:6379'

SGX_URL = 'https://127.0.0.1:1026'

ETH_PRIVATE_KEY = None


for v in list(
    filter(
        lambda v: not v.startswith('__') and v in os.environ,
        globals()
    )
):
    type_ = type(getattr(sys.modules[__name__], v))
    globals()[v] = type_(os.environ[v])
