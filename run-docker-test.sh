#!/usr/bin/env bash
set -ae

export ENDPOINT=http://127.0.0.1:1919
export SKALE_DIR=./tests/data-volumes/skale-dir

create_skale_dir() {
    mkdir -p $SKALE_DIR/node_data/log
}

run_containers() {
    echo $SKALE_DIR
    SKALE_DIR=$SKALE_DIR docker-compose up --build --force-recreate -d
}

run_tests() {
    pytest tests/docker_test.py
}

shutdown_containers() {
    SKALE_DIR=$SKALE_DIR docker-compose down --rmi local
}


cleanup_dot_skale() {
    rm -r --interactive=never $SKALE_DIR
}

create_skale_dir
run_containers
run_tests
# shutdown_containers
# cleanup_dot_skale
