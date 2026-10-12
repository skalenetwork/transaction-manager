#!/usr/bin/env bash
set -ae

: "${ENDPOINT?Need to set ENDPOINT}"
: "${ETH_PRIVATE_KEY?Need to set ETH_PRIVATE_KEY}"


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR=$(dirname $DIR)

cd $PROJECT_DIR

export SKALE_DIR=./tests/data-volumes/skale-dir
export REDIS_DIR=./tests/data-volumes/redis-dir
export SGX_DIR=./tests/data-volumes/skale-dir/node_data/sgx-dir
export PYTHONPATH=${PYTHONPATH}:${PROJECT_DIR}

create_skale_dir() {
    mkdir -p $SKALE_DIR/node_data/log
}

create_redis_dir() {
    mkdir -p $REDIS_DIR/redis-data
    mkdir -p $REDIS_DIR/redis-config
    cp tests/utils/redis.conf $REDIS_DIR/redis-config
}

copy_settings_files() {
    cp -r $PROJECT_DIR/tests/settings $SKALE_DIR/node_data/settings/
}

build() {
    docker compose build --force-rm $@
}

run_containers() {
    docker compose up -d $@
}

shutdown_containers() {
    docker compose down --rmi local
}

cleanup_skale_dir() {
    if [ -d $SKALE_DIR ]; then
        sudo rm -rf $SKALE_DIR
    fi
}

cleanup_redis_dir() {
    if [ -d $REDIS_DIR ]; then
        sudo rm -rf $REDIS_DIR
    fi
}

gen_sgx_key() {
    python3 tests/gen_sgx.py
}

wait_for_hnode() {
    local retries=60
    local rpc_url="http://127.0.0.1:8545"
    local rpc_request='{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'

    until curl --fail --silent \
        --header "Content-Type: application/json" \
        --data "$rpc_request" \
        "$rpc_url" | grep --quiet '"result"'; do
        retries=$((retries - 1))
        if [ "$retries" -eq 0 ]; then
            echo "Hardhat node did not become ready at $rpc_url" >&2
            docker logs hnode --tail 100 >&2
            return 1
        fi
        sleep 1
    done
}

deploy_test_contract() {
    cd tests/tester-contract/
    yarn install
    npx hardhat run --network localhost scripts/deploy.ts
    cd -
}

shutdown_containers
cleanup_skale_dir
cleanup_redis_dir
create_skale_dir
create_redis_dir
copy_settings_files
build tm

if [ -z ${SGX_URL} ]; then
    run_containers tm redis hnode
else
    run_containers sgx tm redis hnode
    gen_sgx_key
fi

wait_for_hnode
deploy_test_contract
