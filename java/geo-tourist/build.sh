#!/bin/bash

. ./env.sh

# Grab static content from Python Flask app
cp ../../templates/index.html ./src/main/resources/static/
rsync -av ../../static ./src/main/resources/static/

./mvnw clean package

