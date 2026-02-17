#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR=$(dirname $DIR)

export ETH_PRIVATE_KEY=$ETH_PRIVATE_KEY
export PYTHONPATH=${PYTHONPATH}:$PROJECT_DIR
export SKALE_DIR=${PROJECT_DIR}/tests/data-volumes/skale-dir
export PYTHONUNBUFFERED=1

uv run pytest -s --log-cli-level=INFO $PROJECT_DIR/tests/docker_test.py $@
