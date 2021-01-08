#!/usr/bin/env bash
set -ea

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR=$(dirname $DIR)

: "${SGX_WALLET_TAG?Need to set SGX_WALLET_TAG}"
export SKALE_DIR_HOST=$PWD/tests/skale-data
export ENDPOINT=$ENDPOINT

VOLUME_DIR="$PWD/tests/data-volumes"
SKALE_DIR="$VOLUME_DIR/skale-dir"
SGX_DIR="$VOLUME_DIR/sgx-dir"
SKALE_NODE_DATA_DIR=$SKALE_DIR/node_data
SKALE_LOG_DIR=$SKALE_NODE_DATA_DIR/log
SGX_CERTS_FOLDER=$SKALE_NODE_DATA_DIR/sgx_certs

mkdir -p "$SKALE_LOG_DIR"
mkdir -p "$SGX_CERTS_FOLDER"
mkdir -p "$SGX_DIR"

export PYTHONPATH=${PYTHONPATH}:$PROJECT_DIR
export TEST_ABI_FILEPATH=${TEST_ABI_FILEPATH:-helper-scripts/contracts_data/manager.json}
export SGX_SERVER_URL=https://127.0.0.1:1026
export SGX_CERTIFICATES_DIR_NAME=sgx_certs
export SKALE_DIR=$SKALE_DIR
export SGX_WALLET_TAG=$SGX_WALLET_TAG
export SGX_DIR=$SGX_DIR
export DEFAULT_GAS_PRICE_WEI=40000000122


docker-compose build --no-cache && docker-compose up -d

sleep 10
