#!/usr/bin/env bash

set -e

: "${VERSION?Need to set VERSION}"
: "${BRANCH?Need to set BRANCH}"

NAME=transaction-manager
REPO_NAME=skalenetwork/$NAME
IMAGE_NAME=$REPO_NAME:$VERSION
LATEST_IMAGE_NAME=$REPO_NAME:$BRANCH-latest

echo "Building $IMAGE_NAME..."
docker build -t $IMAGE_NAME . || exit $?
docker tag $IMAGE_NAME $LATEST_IMAGE_NAME

echo "========================================================================================="
echo "Built $IMAGE_NAME"