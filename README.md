# CockroachDB Geo Tourist

## GIS demo: find pubs, restaurants, cafes, etc. using the spatial features of CockroachDB

![Screenshot restaurants](./restaurants.jpg)

## Setup

[Data set](https://storage.googleapis.com/crl-goddard-gis/osm_1m_eu.txt.gz): 1m
points from OpenStreetMap's Planet Dump, all in Europe

[DDL and sample SQL queries](./osm_crdb.sql): The above mentioned data set is
loaded into one table which has a primary key and one secondary index.  Here is
the DDL:
```
DROP TABLE IF EXISTS osm;
CREATE TABLE osm
(
  id BIGINT
  , date_time TIMESTAMP WITH TIME ZONE
  , uid TEXT
  , name TEXT
  , key_value TEXT[]
  , ref_point GEOGRAPHY
  , geohash4 TEXT -- First 4 characters of geohash, corresponding to a box of about +/- 20 km
  , CONSTRAINT "primary" PRIMARY KEY (geohash4 ASC, id ASC)
);
CREATE INDEX ON osm USING GIN(ref_point);
```

Load the data (see above) using [this script](./load_osm_stdin.py) as follows,
after setting PGHOST, PGPORT, PGUSER, PGPASSWORD, and PGDATABASE to suit your
deployment of CockroachDB:
```
$ export PGHOST=localhost
$ export PGPORT=26257

$ curl -s -k https://storage.googleapis.com/crl-goddard-gis/osm_1m_eu.txt.gz | gunzip - | ./load_osm_stdin.py
```

## Run the app

```
$ export MAPBOX_TOKEN=$( cat ../MapBox_Token.txt )
$ export PGHOST=localhost
$ export PGPORT=26257
```

Optional: disable the use of the GIN index in favor of the primary key index on the geoash substring.
Try both ways (e.g. `unset USE_GEOHASH` vs. `export USE_GEOHASH=true`) and compare the
time it takes to load the amenity icons in the browser.

```
$ export USE_GEOHASH=true
```

## Rebuild the Docker image (optional)

Edit Dockerfile as necessary, and then change `./docker_include.sh` to set
`docker_id` and anything else you'd like to change.

```
$ ./docker_build_image.sh
$ ./docker_tag_publish.sh

```

## Run the app via its Docker image

Edit `./docker_run_image.sh`, changing the environment variables to suit your deployment.

```
$ ./docker_run_image.sh
```

