#!/usr/bin/env python3

import Geohash
import psycopg2
import psycopg2.errorcodes
import logging
import os
import time
from flask import Flask, request, Response, g, render_template
from flask_cors import CORS, cross_origin
import json

#
# Prior to running, set the two required connection parameters as environment variables:
#
#   $ export PGHOST=192.168.1.4
#   $ export PGPORT=5432
#

def db_connect():
  return psycopg2.connect(
    database=os.getenv("PGDATABASE", "defaultdb"),
    user=os.getenv("PGUSER", "root"),
    application_name="Map Client"
  )

def get_db():
  if "db" not in g:
    g.db = db_connect()
  # Handle the case of a closed connection
  try:
    cur = g.db.cursor()
    cur.execute("SELECT 1")
  except psycopg2.OperationalError:
    g.db = db_connect()
  return g.db

app = Flask(__name__)
cors = CORS(app, resources={r'/features': {'origins': '*'}})
with app.app_context():
  get_db()

CHARSET = "utf-8"

def insert_row(sql, do_commit=True):
  conn = get_db()
  with conn.cursor() as cur: # FIXME: Here's what it can fail due to closed connection
    try:
      cur.execute(sql)
    except:
      logging.debug("INSERT: {}".format(cur.statusmessage))
      return
  if do_commit:
    try:
      conn.commit()
    except:
      logging.debug("COMMIT: {}".format(cur.statusmessage))
      print("Retrying commit() in 1 s")
      time.sleep(1)
      conn.commit()

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
  # FIXME: Use the query that hits the spatial index (GIN)
  sql = """
  WITH q1 AS
  (
    SELECT
      name,
      ST_Distance(ST_MakePoint(%s, %s)::GEOGRAPHY, ref_point)::NUMERIC(9, 2) dist_m,
      ST_Y(ref_point::GEOMETRY) lat,
      ST_X(ref_point::GEOMETRY) lon,
      date_time,
      key_value
    FROM osm
    WHERE
      geohash4 = SUBSTRING(%s FOR 4)
  """
  sql += "AND key_value && '{amenity=" + amenity + "}'" # FIXME: how does this work with bind variables?
  sql += """
  )
  SELECT * FROM q1
  WHERE dist_m < 5.0E+03
  ORDER BY dist_m ASC
  LIMIT 10;
  """
  rv = []
  conn = get_db()
  with conn.cursor() as cur:
    try:
      cur.execute(sql, (lon, lat, geohash))
      for row in cur:
        (name, dist_m, lat, lon, dt, kv) = row
        d = {}
        d["name"] = name
        d["amenity"] = amenity
        d["dist_m"] = str(dist_m)
        d["lat"] = lat
        d["lon"] = lon
        #print("Feature: " + json.dumps(d))
        rv.append(d)
    except:
      logging.debug("Search: status message: {}".format(cur.statusmessage))
  return Response(json.dumps(rv), status=200, mimetype="application/json")

@app.route("/")
def index():
  return render_template("index.html", mapbox_token=os.getenv("MAPBOX_TOKEN", "MAPBOX_TOKEN_NOT_SET"))

if __name__ == '__main__':
  port = int(os.getenv("FLASK_PORT", 18080))
  app.run(host='0.0.0.0', port=port, threaded=True, debug=True)
  # Shut down the DB connection when app quits
  with app.app_context():
    get_db().close()

