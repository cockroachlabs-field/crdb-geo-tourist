#!/bin/bash

. ./docker_include.sh

img="$docker_id/$img_name"
tag="1.0"

export PGHOST="host.docker.internal"
export PGPORT="26257"
export PGDATABASE="defaultdb"
export PGUSER="root"
export PGPASSWORD=""
export MAPBOX_TOKEN=$( cat ../MapBox_Token.txt )
export USE_GEOHASH=False

docker pull $img:$tag
docker run -e PGHOST -e PGPORT -e PGDATABASE -e PGUSER -e PGPASSWORD -e MAPBOX_TOKEN --publish 18080:18080 $img

