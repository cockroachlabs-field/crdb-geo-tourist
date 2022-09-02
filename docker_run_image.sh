#!/bin/bash

. ./docker_include.sh

img="$docker_id/$img_name"
tag="1.5"

export DB_URL="postgres://tourist:tourist@host.docker.internal:26257/defaultdb"
export USE_GEOHASH=True

docker pull $img:$tag
docker run -e PGHOST -e PGPORT -e PGDATABASE -e PGUSER -e PGPASSWORD -e MAPBOX_TOKEN -e USE_GEOHASH --publish 18080:18080 $img

