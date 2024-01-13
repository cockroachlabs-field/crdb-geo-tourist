#!/usr/bin/env python3

import Geohash
import psycopg2
from psycopg2.errors import SerializationFailure
import sqlalchemy
from sqlalchemy import create_engine, text, event
import logging
from flask import Flask, request, Response, render_template
import re, os, sys, time, random, json

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

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")

db_url = re.sub(r"^postgres(ql)?", "cockroachdb", db_url)
engine = create_engine(db_url, pool_size=20, pool_pre_ping=True,
  connect_args = { "application_name": "CRDB Geo Tourist" })

@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
  cursor_obj = dbapi_connection.cursor()
  cursor_obj.execute("SET default_transaction_use_follower_reads = on;")
  cursor_obj.close()

# Returns list of tuples: [(x11, x12), (x21, x22), ...]
def run_stmt(stmt, max_retries=3):
  rv = []
  for retry in range(0, max_retries):
    if retry > 0:
      logging.warning("Retry number {}".format(retry))
    try:
      with engine.connect() as conn:
        rs = conn.execute(stmt)
        for row in rs:
          rv.append(row)
      return rv
    except SerializationFailure as e:
      logging.warning("Error: %s", e)
      logging.warning("EXECUTE SERIALIZATION_FAILURE BRANCH")
      sleep_s = (2**retry) * 0.1 * (random.random() + 0.5)
      logging.warning("Sleeping %s s", sleep_s)
      time.sleep(sleep_s)
    except (sqlalchemy.exc.OperationalError, psycopg2.OperationalError) as e:
      # Get a new connection and try again
      logging.warning("Error: %s", e)
      logging.warning("EXECUTE CONNECTION FAILURE BRANCH")
      sleep_s = 0.12 + random.random() * 0.25
      logging.warning("Sleeping %s s", sleep_s)
      time.sleep(sleep_s)
    except psycopg2.Error as e:
      logging.warning("Error: %s", e)
      logging.warning("EXECUTE DEFAULT BRANCH")
      raise e
  raise ValueError(f"Transaction did not succeed after {max_retries} retries")

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
  for row in run_stmt(stmt):
    (rv["lat"], rv["lng"]) = row # Returns a single row
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
  logging.info("Tourist: %s", json.dumps(obj))
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
  logging.debug("SQL: %s", sql)
  stmt = None
  if useGeohash:
    stmt = text(sql).bindparams(lon_val=lon, lat_val=lat, geohash=geohash, amenity=amenity)
  else:
    stmt = text(sql).bindparams(lon_val=lon, lat_val=lat, amenity="amenity=" + amenity)
  for row in run_stmt(stmt):
    (name, dist_m, lat, lon, dt, kv, rating) = row
    d = {}
    d["name"] = name
    d["amenity"] = amenity
    d["dist_m"] = str(dist_m)
    d["lat"] = lat
    d["lon"] = lon
    d["rating"] = "Rating: " + (str(rating) + " out of 5" if rating is not None else "(not rated)")
    logging.debug("Feature: %s", json.dumps(d))
    rv.append(d)
  return Response(json.dumps(rv), status=200, mimetype="application/json")

@app.route("/")
def index():
  return render_template("index.html")

if __name__ == '__main__':
  port = int(os.getenv("FLASK_PORT", 18080))
  useGeohash = (os.getenv("USE_GEOHASH", "true").lower() == "true")
  print("useGeohash = %s" % ("True" if useGeohash else "False"))
  from waitress import serve
  serve(app, host="0.0.0.0", port=port, threads=10)
  # Shut down the DB connection when app quits
  engine.dispose()

