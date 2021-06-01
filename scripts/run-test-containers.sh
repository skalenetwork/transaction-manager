#!/usr/bin/env bash
set -ae

: "${ENDPOINT?Need to set ENDPOINT}"
: "${ETH_PRIVATE_KEY?Need to set ETH_PRIVATE_KEY}"


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR=$(dirname $DIR)

cd $PROJECT_DIR

export SKALE_DIR=./tests/data-volumes/skale-dir
export REDIS_DIR=./tests/data-volumes/redis-dir

create_skale_dir() {
    mkdir -p $SKALE_DIR/node_data/log
}

create_redis_dir() {
    mkdir -p $REDIS_DIR/redis-data
    mkdir -p $REDIS_DIR/redis-config
    cp tests/utils/redis.conf $REDIS_DIR/redis-config
}

run_containers() {
    docker-compose up --build --force-recreate -d
}

shutdown_containers() {
    docker-compose down --rmi local
}


cleanup_skale_dir() {
    rm -r --interactive=never $SKALE_DIR
}

cleanup_redis_dir() {
    rm -r --interactive=never $REDIS_DIR
}

shutdown_containers
cleanup_skale_dir
cleanup_redis_dir
create_skale_dir
create_redis_dir
run_containers
