import json
import os

from .config import NODE_DATA_PATH

NODE_CONFIG_FILEPATH = os.path.join(NODE_DATA_PATH, 'node_config.json')


def is_config_created() -> bool:
    return os.path.isfile(NODE_CONFIG_FILEPATH)


def get_sgx_keyname() -> str:
    with open(NODE_CONFIG_FILEPATH, encoding='utf-8') as data_file:
        config = json.loads(data_file.read())
    return config['sgx_key_name']
