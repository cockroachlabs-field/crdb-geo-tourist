#!/bin/bash

. ./docker_include.sh

# For running on Mac with CockroachDB instance on localhost (insecure mode)
export DB_URL="jdbc:cockroachdb://host.docker.internal:26257/defaultdb?ssl=false&retryConnectionErrors=true&retryTransientErrors=true"
export FLASK_PORT=8081

docker run -e DB_URL -e FLASK_PORT -p $FLASK_PORT:$FLASK_PORT $docker_id/$img_name

