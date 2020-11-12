#!/bin/bash

file="./planet-latest.osm.pbf"
osmosis="./osmosis-0.48.2"

# INFO: Total execution time: 141945458 milliseconds.
# ./planet_osm_extract.sh  109631.24s user 1357.06s system 78% cpu 39:25:46.14 total
$osmosis/package/bin/osmosis --read-pbf-0.6 file=$file \
  --bounding-box top=72.253800 left=-12.666450 bottom=33.120960 right=34.225994 \
  --write-xml file=- | bzip2 > extracted.osm.bz2

