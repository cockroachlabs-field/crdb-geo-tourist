#!/bin/bash

. ./env.sh

# Grab static content from Python Flask app
cp ../../templates/index.html ../../static/* ./src/main/resources/static/

./gradlew clean build

