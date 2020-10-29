#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR=$(dirname $DIR)

: "${SGX_WALLET_TAG?Need to set SGX_WALLET_TAG}"

VOLUME_DIR=tests/data-volumes
SKALE_DIR=$PWD/tests/data-volumes/skale-dir
SGX_DIR=$PWD/tests/data-volumes/sgx-dir
REDIS_DIR=$PWD/tests/data-volumes/redis-dir
REDIS_DATA_DIR=$REDIS_DIR/redis-data
REDIS_CONFIG_DIR=$REDIS_DIR/redis-config
SKALE_NODE_DATA_DIR=$SKALE_DIR/node_data
SKALE_LOG_DIR=$SKALE_NODE_DATA_DIR/log
SKALE_CONTRACTS_INFO=$SKALE_DIR/contracts_info

mkdir -p $SKALE_LOG_DIR
mkdir -p $REDIS_CONFIG_DIR $REDIS_DATA_DIR
mkdir -p $SGX_DIR
cp tests/test-redis.conf $REDIS_CONFIG_DIR/redis.conf

export ENDPOINT=http://127.0.0.1:8545
export PYTHONPATH=$PROJECT_DIR
export TEST_ABI_FILEPATH=${TEST_ABI_FILEPATH:-helper-scripts/manager.json}
export SGX_SERVER_URL=https://127.0.0.1:1026
export REDIS_URI=redis://127.0.0.1:6379
export SGX_CERTIFICATES_FOLDER_NAME=sgx_certs
export SKALE_DIR=$SKALE_DIR
export SGX_WALLET_TAG=$SGX_WALLET_TAG
export REDIS_DATA_DIR=$REDIS_DATA_DIR
export REDIS_CONFIG_DIR=$REDIS_CONFIG_DIR
export SGX_DIR=$SGX_DIR


docker-compose build --no-cache && docker-compose up -d

echo 'Wating for sgx initialization ...'
sleep 50

TEST_DATA_DIR='helper-scripts/contracts_data/manager.json'

NODE_DATA_PATH=$SKALE_NODE_DATA_DIR \
STDERR_LOG=True \
TEST_ABI_FILEPATH=$TEST_ABI_FILEPATH \
    py.test \
    --cov-report term-missing --cov=. --capture no \
    $PROJECT_DIR/tests/main_test.py

# TEST_DATA_DIR=$SKALE_DIR_HOST SGX_WALLET_TAG=$SGX_WALLET_TAG docker-compose down
# TEST_DATA_DIR=$SKALE_DIR_HOST SGX_WALLET_TAG=$SGX_WALLET_TAG docker-compose rm -f
# rm -r $VOLUME_DIR/*
