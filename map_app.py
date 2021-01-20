#!/usr/bin/env python3

import Geohash
import psycopg2
import psycopg2.errorcodes
import logging
import os
from flask import Flask, request, Response, g, render_template
import json

useGeohash = False
database = os.getenv("PGDATABASE", "defaultdb")

# Environment variables influencing the connection:
# PGHOST, PGPORT, PGUSER, PGPASSWORD, and PGDATABASE
def db_connect():
  return psycopg2.connect(
    database=database,
    user=os.getenv("PGUSER", "root"),
    password=os.getenv("PGPASSWORD", ""),
    application_name="CRDB Geo Tourist"
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
with app.app_context():
  get_db()

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
  rv = { "lat": 51.506712, "lon": -0.127235 } # Default tourist location, if none are enabled
  conn = get_db()
  with conn.cursor() as cur:
    try:
      cur.execute(sql)
      (rv["lat"], rv["lng"]) = cur.fetchone()
    except:
      logging.debug("Search: status message: {}".format(cur.statusmessage))
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
      ST_Distance(ST_MakePoint(%s, %s)::GEOGRAPHY, ref_point)::NUMERIC(9, 2) dist_m,
      ST_Y(ref_point::GEOMETRY) lat,
      ST_X(ref_point::GEOMETRY) lon,
      date_time,
      key_value
    FROM osm
    WHERE
  """
  if useGeohash:
    sql += "geohash4 = SUBSTRING(%s FOR 4)"
  else:
    sql += "ST_DWithin(ST_MakePoint(%s, %s)::GEOGRAPHY, ref_point, 5.0E+03, TRUE)"
  sql += """
      AND key_value && ARRAY[%s]
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
  conn = get_db()
  with conn.cursor() as cur:
    try:
      if useGeohash:
        cur.execute(sql, (lon, lat, geohash, "amenity=" + amenity))
      else:
        cur.execute(sql, (lon, lat, lon, lat, "amenity=" + amenity))
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
  useGeohash = (os.getenv("USE_GEOHASH", "false").lower() == "true")
  print("useGeohash = %s" % ("True" if useGeohash else "False"))
  is_debug = True
  if "KUBERNETES_SERVICE_HOST" in os.environ:
    is_debug = False
  app.run(host='0.0.0.0', port=port, threaded=True, debug=is_debug)
  # Shut down the DB connection when app quits
  with app.app_context():
    get_db().close()

