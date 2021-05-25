#!/bin/bash

. ./docker_include.sh

img="$docker_id/$img_name"
tag="1.2"

export PGHOST="host.docker.internal"
export PGPORT="26257"
export PGDATABASE="defaultdb"
export PGUSER="tourist"
export PGPASSWORD="tourist"
export USE_GEOHASH=True

docker pull $img:$tag
docker run -e PGHOST -e PGPORT -e PGDATABASE -e PGUSER -e PGPASSWORD -e MAPBOX_TOKEN -e USE_GEOHASH --publish 18080:18080 $img

