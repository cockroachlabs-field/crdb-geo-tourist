#!/usr/bin/env python3

import Geohash
import psycopg2
import psycopg2.errorcodes
import sqlalchemy
from sqlalchemy import create_engine, text
import logging
import os, sys
from flask import Flask, request, Response, g, render_template
import json
import re

useGeohash = False

#
# Set the following environment variables:
#
#  export DB_URL="postgres://user:passwd@localhost:26257/defaultdb"
#  export FLASK_PORT=18080
#  export USE_GEOHASH=true
#

db_url = os.getenv("DB_URL")
if db_url is None:
  print("Environment DB_URL must be set. Quitting.")
  sys.exit(1)

db_url = re.sub(r"^postgres", "cockroachdb", db_url)
engine = create_engine(db_url, pool_size=20, pool_pre_ping=True,
  connect_args = { "application_name": "CRDB Geo Tourist" })

app = Flask(__name__)

# Return a JSON list of the sites where the tourist may be located
@app.route("/sites", methods = ['GET'])
def sites():
  sql = """
  SELECT lat, lon
  FROM tourist_locations
  WHERE enabled = TRUE
  ORDER BY RANDOM()
  LIMIT 1;
  """
  stmt = text(sql)
  rv = { "lat": 51.506712, "lon": -0.127235 } # Default tourist location, if none are enabled
  with engine.connect() as conn:
    rs = conn.execute(stmt)
    for row in rs:
      (rv["lat"], rv["lng"]) = row
  return Response(json.dumps(rv), status=200, mimetype="application/json")

# Return a JSON list of the top 10 nearest features of type <amenity>
# TODO: parameterize max. dist., limit; handle mutiple features
@app.route("/features", methods = ['POST'])
def features():
  obj = request.get_json(force=True)
  lat = float(obj["lat"])
  lon = float(obj["lon"])
  amenity = obj["amenity"]
  geohash = Geohash.encode(lat, lon)
  obj["geohash"] = geohash
  print(json.dumps(obj))
  sql = """
  WITH q1 AS
  (
    SELECT
      name,
      ST_Distance(ST_MakePoint(:lon_val, :lat_val)::GEOGRAPHY, ref_point)::NUMERIC(9, 2) dist_m,
      ST_Y(ref_point::GEOMETRY) lat,
      ST_X(ref_point::GEOMETRY) lon,
      date_time,
      key_value,
      rating
    FROM osm
    WHERE
  """
  if useGeohash:
    sql += "geohash4 = SUBSTRING(:geohash FOR 4) AND amenity = :amenity"
  else:
    sql += "ST_DWithin(ST_MakePoint(:lon_val, :lat_val)::GEOGRAPHY, ref_point, 5.0E+03, TRUE)"
    sql += " AND key_value && ARRAY[:amenity]"
  sql += """
  )
  SELECT * FROM q1
  """
  if useGeohash:
    sql += "WHERE dist_m < 5.0E+03"
  sql += """
  ORDER BY dist_m ASC
  LIMIT 10;
  """
  rv = []
  #print("SQL:\n" + sql + "\n")
  stmt = None
  if useGeohash:
    stmt = text(sql).bindparams(lon_val=lon, lat_val=lat, geohash=geohash, amenity=amenity)
  else:
    stmt = text(sql).bindparams(lon_val=lon, lat_val=lat, geohash=geohash, amenity="amenity=" + amenity)
  with engine.connect() as conn:
    rs = conn.execute(stmt)
    for row in rs:
      (name, dist_m, lat, lon, dt, kv, rating) = row
      d = {}
      d["name"] = name
      d["amenity"] = amenity
      d["dist_m"] = str(dist_m)
      d["lat"] = lat
      d["lon"] = lon
      d["rating"] = "Rating: " + (str(rating) + " out of 5" if rating is not None else "(not rated)")
      #print("Feature: " + json.dumps(d))
      rv.append(d)
  return Response(json.dumps(rv), status=200, mimetype="application/json")

@app.route("/")
def index():
  return render_template("index.html")

if __name__ == '__main__':
  port = int(os.getenv("FLASK_PORT", 18080))
  useGeohash = (os.getenv("USE_GEOHASH", "false").lower() == "true")
  print("useGeohash = %s" % ("True" if useGeohash else "False"))
  is_debug = True
  if "KUBERNETES_SERVICE_HOST" in os.environ:
    is_debug = False
  app.run(host='0.0.0.0', port=port, threaded=True, debug=is_debug)
  # Shut down the DB connection when app quits
  engine.dispose()

