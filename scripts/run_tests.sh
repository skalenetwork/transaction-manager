#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR=$(dirname $DIR)

: "${SGX_WALLET_TAG?Need to set SGX_WALLET_TAG}"

export SKALE_DIR_HOST=$PWD/tests/skale-data
export ENDPOINT=http://localhost:8545

export PYTHONPATH=$PROJECT_DIR
export FLASK_APP_HOST=0.0.0.0
export FLASK_APP_PORT=3008
export FLASK_DEBUG_MODE=True
export FLASK_SECRET_KEY=123
export TEST_ABI_FILEPATH=test_abi.json
export SGX_SERVER_URL=https://127.0.0.1:1026
export REDIS_URI=redis://localhost:6379

mkdir -p $SKALE_DIR_HOST/sgx-data
mkdir -p $SKALE_DIR_HOST/redis-data
mkdir -p $SKALE_DIR_HOST/redis-config

TEST_DATA_DIR=$SKALE_DIR_HOST SGX_WALLET_TAG=$SGX_WALLET_TAG docker-compose up -d

py.test $PROJECT_DIR/tests/queue_test.py

# TEST_DATA_DIR=$SKALE_DIR_HOST SGX_WALLET_TAG=$SGX_WALLET_TAG docker-compose down
# TEST_DATA_DIR=$SKALE_DIR_HOST SGX_WALLET_TAG=$SGX_WALLET_TAG docker-compose rm -f
