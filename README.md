# CockroachDB Geo Tourist

## Use the spatial features in CockroachDB to find pubs, restaurants, cafes, etc.

![Screenshot restaurants](./restaurants.jpg)
(App shown running on a laptop)

This is a simple Python Flask and Javascript app which illustrates some of the
new spatial capabilities in CockroachDB 20.2.  The scenario is this: in the web
app, an icon represents the user, and this user is situated at a location
randomly chosen from a set of destinations, each time the page is refreshed.
Then, a REST call is made from the Javascript front end, including the type of
_amenity_ to search for as well as the user's location.  Witin the Python Flask
app, those values are featured in a SQL query against a CockroachDB instance
loaded with spatial data.  This query uses the following spatial data types,
operators, and indexes to find and return a set of the nearest amenities,
sorted by distance:

1. `GEOGRAPHY`: the data type to represent each of the `POINT` data elements associated with the amenity
1. `ST_Distance`: used to calculate the distance from the user to each of these locations
1. `ST_Y` and `ST_X`: are used to retrieve the longitude and latitude of each of these points, for plotting onto the map
1. `ST_DWithin`: used in the `WHERE` clause of the SQL query to constrain the results to points within 5km of the user's location
1. `ST_MakePoint`: converts the longitude and latitude representing the user's location into a `POINT`
1. A GIN index on the `ref_point` column in the `osm` table speeds up the calculation done by `ST_DWithin`

These types, operators, and the GIN index are familiar to users of
[PostGIS](https://postgis.net/), the popular spatial extension available for
PostgreSQL.  In CockroachDB, this layer was created from scratch and PostGIS
was not used, but the PostGIS API was preserved.

One aspect of CockroachDB's spatial capability is especially interesting: the
way the spatial index works.  In order to preserve CockroachDB's unique ability
to scale horizontally by adding nodes to a running cluster, its approach to
spatial indexing is to decompose of the space being indexed into buckets of
various sizes.  A deeper discussion of this topic is available
[here](https://www.cockroachlabs.com/docs/v20.2/spatial-indexes).

<img src="./mobile_view.png" width="360" alt="Running on iPhone">
(App running in an iPhone, in Safari)

The demo can be run locally, in a Docker container, or in K8s.

## Data

The data set is a sample of an extract of the OpenStreetMap
Planet Dump which is accessible from [here](https://wiki.openstreetmap.org/wiki/Planet.osm).
The `planet-latest.osm.pbf` file was downloaded (2020-08-01) and then processed
using [Osmosis](https://github.com/openstreetmap/osmosis/releases) as
documented in [this script](./osm/planet_osm_extract.sh).  The bounding box
specified for the extract was `--bounding-box top=72.253800 left=-12.666450 bottom=33.120960 right=34.225994`,
corresponding to the area shown in the figure below.  The result of this operation
was a 36 GB Bzip'd XML file (not included here).  This intermediate file was then
processed using [this Perl script](./osm/extract_points_from_osm_xml.pl), with the
result being piped through Gzip to produce a [smaller data
set](https://storage.googleapis.com/crl-goddard-gis/osm_1m_eu.txt.gz) consisting of 1 million points.

![Boundary of OSM data extract](./osm/OSM_extracted_region.jpg)

[DDL and sample SQL queries](./osm/osm_crdb.sql): The data set is loaded into
one table which has a primary key and one secondary index.  Here is the DDL:

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
**NOTE:** `./load_osm_stdin.py` creates the `osm` table and the GIN index if they don't already exist.

[The Flask app](./map_app.py) runs one of two variations of a query, depending on whether the
environment variable `USE_GEOHASH` is set and, if so, its value (`true` or `false`), as shown in
the following code block (line numbers have been added here).  The main difference is that, when
`USE_GEOHASH` is set to `true`, the GIN index is not used, but rather the four character substring
of the geohash of the point is used, which effectively constrains the search area to a +/- 20 km
box.  This `geohash4` column is the leading component of the primary key, so is indexed, allowing
this to perform very well while also having lower impact on data load speeds.  Now, if this query
was more complex than "find me the N closest points within a radius of X", the GIN index would be
preferable since it permits far more complex comparisons.

```
 1	  sql = """
 2	  WITH q1 AS
 3	  (
 4	    SELECT
 5	      name,
 6	      ST_Distance(ST_MakePoint(%s, %s)::GEOGRAPHY, ref_point)::NUMERIC(9, 2) dist_m,
 7	      ST_Y(ref_point::GEOMETRY) lat,
 8	      ST_X(ref_point::GEOMETRY) lon,
 9	      date_time,
10	      key_value
11	    FROM osm
12	    WHERE
13	  """
14	  if useGeohash:
15	    sql += "geohash4 = SUBSTRING(%s FOR 4)"
16	  else:
17	    sql += "ST_DWithin(ST_MakePoint(%s, %s)::GEOGRAPHY, ref_point, 5.0E+03, TRUE)"
18	  sql += """
19	      AND key_value && ARRAY[%s]
20	  )
21	  SELECT * FROM q1
22	  """
23	  if useGeohash:
24	    sql += "WHERE dist_m < 5.0E+03"
25	  sql += """
26	  ORDER BY dist_m ASC
27	  LIMIT 10;
28	  """
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

## Deploy the app in Kubernetes (K8s)

```
$ kubectl describe service crdb-geo-tourist-lb
Name:                     crdb-geo-tourist-lb
Namespace:                default
Labels:                   <none>
Annotations:              <none>
Selector:                 app=crdb-geo-tourist
Type:                     LoadBalancer
IP:                       10.63.243.111
LoadBalancer Ingress:     35.188.226.10
Port:                     <unset>  80/TCP
TargetPort:               18080/TCP
NodePort:                 <unset>  32456/TCP
Endpoints:                10.60.2.7:18080,10.60.3.7:18080
Session Affinity:         None
External Traffic Policy:  Cluster
Events:
  Type    Reason                Age    From                Message
  ----    ------                ----   ----                -------
  Normal  EnsuringLoadBalancer  8m40s  service-controller  Ensuring load balancer
  Normal  EnsuredLoadBalancer   8m1s   service-controller  Ensured load balancer
```

Enter the value associated with `LoadBalancer Ingress:` into your Web browser to see the app running.

