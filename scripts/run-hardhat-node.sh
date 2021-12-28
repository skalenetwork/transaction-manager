#!/usr/bin/env bash
set -ae

run_container() {
    docker-compose up --build --force-recreate -d hardhat-node
}

shutdown_container() {
    docker-compose down --rmi local
}

# shutdown_container
run_container
