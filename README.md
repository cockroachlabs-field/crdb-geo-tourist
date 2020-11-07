# CockroachDB Geo Tourist

## GIS demo: find pubs, restaurants, cafes, etc. using the spatial features of CockroachDB

![Screenshot restaurants](./restaurants.jpg)

## Run the app

```
$ export MAPBOX_TOKEN=$( cat ../MapBox_Token.txt )
$ export PGHOST=localhost
$ export PGPORT=26257
```

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

Load the data (see above) using [this script](./load_osm_offset.py) as follows
(PGUSER, PGPASSWORD, PGDATABASE may also need to be set, depending on your
deployment of CockroachDB):
```
$ export PGHOST=localhost
$ export PGPORT=26257
$ ./load_osm_no_staging.py osm_1m_eu.txt.gz 1000000 0
```

