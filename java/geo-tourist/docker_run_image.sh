#!/bin/bash

. ./docker_include.sh

# For running on Mac with CockroachDB instance on localhost (insecure mode)
export DB_URL="jdbc:postgresql://host.docker.internal:26257/defaultdb?user=root&ssl=false"
export USE_GEOHASH=True
export FLASK_PORT=8081

docker run -e DB_URL -e FLASK_PORT -e USE_GEOHASH -p $FLASK_PORT:$FLASK_PORT $docker_id/$img_name

