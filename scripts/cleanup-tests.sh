#!/usr/bin/env bash

docker-compose down
echo 'WARNING the following command will be executed with sudo!'
sudo rm -rf tests/data-volumes/*
