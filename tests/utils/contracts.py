import json
import os
from pathlib import Path


DIR_PATH = Path(os.path.realpath(__file__)).parents[2].absolute()
TESTER_CONTRACT_PATH = os.path.join(DIR_PATH, 'tests', 'tester-contract', 'abi.json')


def get_tester_abi():
    with open(TESTER_CONTRACT_PATH) as abi_file:
        return json.load(abi_file)
