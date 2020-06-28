#!/usr/bin/env bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
PROJECT_DIR=$(dirname $DIR)

export SKALE_DIR_HOST=$PWD/tests/skale-data
export ENDPOINT=http://localhost:8545

export PYTHONPATH=$PROJECT_DIR
export FLASK_APP_HOST=0.0.0.0
export FLASK_APP_PORT=3008
export FLASK_DEBUG_MODE=True
export FLASK_SECRET_KEY=123

export PK_FILE=$PROJECT_DIR/pk_file

echo $ETH_PRIVATE_KEY > $PROJECT_DIR/pk_file

py.test $PROJECT_DIR/tests/
