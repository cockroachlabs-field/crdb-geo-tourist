#!/usr/bin/env python3

"""

  * Generate a geohash of the (lat, lon)
  * Add the geohash and some shortened versions to the JSON (See https://github.com/vinsci/geohash/)
    - pip3 install Geohash
    - geohash = Geohash.encode(lat, lon)
    - geohash precision: https://gis.stackexchange.com/questions/115280/what-is-the-precision-of-a-geohash
  * Store entire record as JSONB
  * Index the JSONB
  * Pull out id, timestamp, the 4-char geohash, and a GEOGRAPHY as separate columns
  * PK => (geohash4, id)
  * Pub review sources:
    - https://whatpub.com/

  * ./osm_xml_to_json.py extracted.osm.bz2 5000000  5567.39s user 28.17s system 6% cpu 25:15:00.26 total
  * cockroach dump defaultdb osm_json --insecure  279.00s user 61.36s system 179% cpu 3:10.11 total
  * gzip - > backup.sql.gz  57.24s user 1.92s system 31% cpu 3:10.11 total

  * DDL:

    DROP TABLE IF EXISTS osm_json;
    CREATE TABLE osm_json
    (
      id STRING
      , geo_20km CHAR(4)
      , ts TIMESTAMP
      , x GEOGRAPHY
      , obj JSONB
      ,  PRIMARY KEY (geo_20km ASC, id ASC)
    );

"""

import sys
import os
import json
import bz2
import re
import Geohash
import psycopg2
import psycopg2.errorcodes
import psycopg2.extras
import html
import time

# Example input data
"""
  <node id="114" version="4" timestamp="2018-07-21T22:01:43Z" uid="207581" user="Hjart" changeset="60940511" lat="59.9506757" lon="10.784339"/>
  <node id="115" version="3" timestamp="2018-07-21T22:01:43Z" uid="207581" user="Hjart" changeset="60940511" lat="59.9510531" lon="10.7796921"/>
  ...
  <node id="108042" version="22" timestamp="2019-11-07T19:01:18Z" uid="2773866" user="kreuzschnabel" changeset="76773501" lat="51.5235613" lon="-0.1355134">
    <tag k="name" v="Simmons"/>
    <tag k="amenity" v="pub"/>
    <tag k="toilets" v="yes"/>
    <tag k="old_name" v="The Jeremy Bentham"/>
    <tag k="addr:street" v="University Street"/>
    <tag k="addr:postcode" v="WC1E 6JL"/>
    <tag k="contact:phone" v="+44 20 73771843"/>
    <tag k="opening_hours" v="Mo-We 16:00-23:30; Th-Fr 16:00-01:00; Sa 16:00-23:30"/>
    <tag k="contact:website" v="http://www.simmonsbar.co.uk/euston-square/4593769006"/>
    <tag k="addr:housenumber" v="31"/>
  </node>

"""

if len(sys.argv) != 3:
  print("Usage: %s osm_xml.bz2 max_points" % sys.argv[0])
  sys.exit(1)

in_file = sys.argv[1]
max_points = int(sys.argv[2])

conn = psycopg2.connect(
  database=os.getenv("PGDATABASE", "defaultdb")
  , user=os.getenv("PGUSER", "root")
  , port=int(os.getenv("PGPORT", "26257"))
  , host=os.getenv("PGHOST", "localhost")
  , application_name="OSM JSON"
)
conn.autocommit = True

# rows is a list of lists
def do_inserts (conn, rows):
  t0 = time.time()
  with conn.cursor() as cur:
    """
    psycopg2.extras.execute_batch(cur, "INSERT INTO osm_json (id, geo_20km, ts, x, obj)"
      + "VALUES (%s, %s, %s, ST_MakePoint(%s, %s)::GEOGRAPHY, %s::JSONB)",
      rows, page_size=100)
    """
  print("INSERTED %d rows in %.2f seconds" % (len(rows), time.time() - t0))

n_read = 0
kv = {}
node = {}
batch_size = 1000

# See above data examples for how this is derived
node_pat = re.compile(r'<node id="([^"]+)" version="(\d+)" timestamp="([^"]+)" uid="(\d+)" user="([^"]+)" changeset="(\d+)" lat="(-?\d+\.\d+)" lon="(-?\d+\.\d+)">')
tag_pat = re.compile(r'^<tag +k="([^"]+)" +v="([^"]+)" */>$')

rows = []
with bz2.open(in_file, mode="rt", encoding="utf8", newline='\n') as f:
  while n_read < max_points:
    line = f.readline().strip()
    if line.startswith("</node>"):
      if not bool(node) or not bool(kv): # Is either empty?
        continue
      if "name" in kv: # I think it's interesting only is it has a name
        node["kv"] = kv
        rows.append([node["id"], node["geo_20km"], node["timestamp"], node["lon"], node["lat"], json.dumps(node)])
        if len(rows) == batch_size:
          do_inserts(conn, rows)
          rows = []
        #print(json.dumps(node))
        n_read += 1
    elif line.startswith("<node "):
      if line.endswith("/>"):
        continue
      node.clear()
      kv.clear()
      m = node_pat.match(line)
      if m is not None:
        node["id"] = m.group(1)
        node["version"] = m.group(2)
        node["timestamp"] = m.group(3)
        node["uid"] = m.group(4)
        node["user"] = html.unescape(m.group(5))
        node["changeset"] = m.group(6)
        lat = float(m.group(7))
        lon = float(m.group(8))
        node["lat"] = lat
        node["lon"] = lon
        geohash = Geohash.encode(lat, lon)
        # Add some geohash values.  The "20km" suffix means it's accurate to +/- 20 kilometers
        node["geo_20m"] = geohash[0:8]
        node["geo_2400m"] = geohash[0:5]
        node["geo_20km"] = geohash[0:4]
        node["geo_80km"] = geohash[0:3]
      else:
        pass
    elif line.startswith("<tag "):
      m = tag_pat.match(line)
      if m is not None:
        kv[m.group(1)] = html.unescape(str(m.group(2)))
      else:
        pass
if len(rows) > 0:
  do_inserts(conn, rows)
conn.close()

