#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR=$(dirname $DIR)

export ETH_PRIVATE_KEY=$ETH_PRIVATE_KEY
export PYTHONPATH=${PYTHONPATH}:$PROJECT_DIR
py.test $PROJECT_DIR/tests/ \
    --ignore $PROJECT_DIR/tests/docker_test.py \
        --cov-report term-missing \
            --cov $PROJECT_DIR/transaction_manager $@
