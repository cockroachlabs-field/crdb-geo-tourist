#!/usr/bin/env python3

import psycopg2
import psycopg2.errorcodes
import sqlalchemy
from sqlalchemy import create_engine, insert
from sqlalchemy import Table, MetaData
import time
import sys, os
import gzip
import html
import re
import fileinput
import logging

"""
 $ sudo apt install python3-pip
 $ pip3 install psycopg2-binary
 $ pip3 install sqlalchemy
 $ pip3 install sqlalchemy-cockroachdb
"""

#
# Set the following environment variable:
#
#   export DB_URL="postgres://user:passwd@localhost:26257/defaultdb"
#
db_url = os.getenv("DB_URL")
if db_url is None:
  print("Environment DB_URL must be set. Quitting.")
  sys.exit(1)

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")

#
# curl -s -k http://localhost:8000/osm_1m_eu.txt.gz | gunzip - | ./load_osm_stdin.py
#

rows_per_batch = 2048 # Edit as necessary

# This is the list of sites where our "tourist" will initially appear upon a page load
sites = []
sites.append({"name": "British Museum", "lat": 51.519844, "lon": -0.126731})
sites.append({"name": "Trafalgar Square", "lat": 51.506712, "lon": -0.127235})
sites.append({"name": "Tate Modern", "lat": 51.508337, "lon": -0.099281})
sites.append({"name": "Dublin", "lat": 53.346028, "lon": -6.279658})
sites.append({"name": "Munich", "lat": 48.135056, "lon": 11.576097})
sites.append({"name": "Le Marais", "lat": 48.857744, "lon": 2.357768})
sites.append({"name": "Trastevere", "lat": 41.886071, "lon": 12.467422})
sites.append({"name": "Prado Museum", "lat": 40.41367, "lon": -3.69185})
sites.append({"name": "Mercado Antón Martín", "lat": 40.41170, "lon": -3.69850})
sites.append({"name": "Kyiv", "lat": 50.4474203, "lon": 30.5265874})

max_retries = int(os.getenv("MAX_RETRIES", "3"))
logging.info("MAX_RETRIES: {}".format(max_retries))

# Using the CockroachDB dialect
db_url = re.sub(r"^postgres", "cockroachdb", db_url)
logging.info("DB_CONN_STR (rewritten): {}".format(db_url))
engine = create_engine(db_url, connect_args = { "application_name": "OSM Data Loader" })
logging.info("Engine: OK")

def do_inserts(list_of_row_maps):
  for retry in range(1, max_retries + 1):
    try:
      with engine.begin() as conn:
        # https://docs.sqlalchemy.org/en/14/tutorial/data_insert.html
        conn.execute(insert(osm_table), list_of_row_maps)
      return
    except sqlalchemy.exc.OperationalError as e: # This handles dead nodes
      logging.warning(e)
      logging.warning("OperationalError: sleeping 5 seconds")
      time.sleep(5)
    except psycopg2.errors.SerializationFailure as e:
      logging.warning(e)
      sleep_s = (2 ** retry) * 0.1 * (random.random() + 0.5)
      logging.warning("Sleeping %s seconds", sleep_s)
      time.sleep(sleep_s)
    except (sqlalchemy.exc.IntegrityError, psycopg2.errors.UniqueViolation) as e:
      logging.warning(e)
      logging.warning("UniqueViolation: continuing to next TXN")
    except psycopg2.Error as e:
      logging.warning(e)
      logging.warning("Not sure about this one ... sleeping 5 seconds, though")
      time.sleep(5)

def setup_db():
  with engine.begin() as conn:
    sql = """
    CREATE TABLE IF NOT EXISTS osm
    (
      geohash4 TEXT NOT NULL
      , amenity TEXT NOT NULL
      , id BIGINT NOT NULL
      , date_time TIMESTAMP WITH TIME ZONE
      , uid TEXT
      , name TEXT NOT NULL
      , lat FLOAT NOT NULL
      , lon FLOAT NOT NULL
      , key_value TEXT[]
      , search_hints TEXT
      , ref_point GEOGRAPHY AS (ST_MakePoint(lon, lat)::GEOGRAPHY) STORED
      , CONSTRAINT "primary" PRIMARY KEY (geohash4 ASC, amenity ASC, id ASC)
    );
    """
    logging.info("Creating osm table")
    conn.execute(sql)

    # Create the spatial index
    sql = "CREATE INDEX IF NOT EXISTS osm_geo_idx ON osm USING GIST(ref_point);"
    logging.info("Creating index on ref_point")
    conn.execute(sql)

    # Table of positions for the user
    sql = """
    DROP TABLE IF EXISTS tourist_locations;
    CREATE TABLE tourist_locations
    (
      name TEXT
      , lat FLOAT8
      , lon FLOAT8
      , enabled BOOLEAN DEFAULT TRUE
      , geohash CHAR(9) AS (ST_GEOHASH(ST_SETSRID(ST_MAKEPOINT(lon, lat), 4326), 9)) STORED
      , CONSTRAINT "primary" PRIMARY KEY (geohash ASC)
    );
    """
    logging.info("Creating tourist_locations table")
    conn.execute(sql)

    # Populate that with some potential tourist locations
    sql = "INSERT INTO tourist_locations (name, lat, lon) VALUES (%s, %s, %s);"
    logging.info("Populating tourist_locations table")
    for s in sites:
      conn.execute(sql, (s["name"], s["lat"], s["lon"]))

rows = []
llre = re.compile(r"^-?\d+\.\d+$")
bad_re = re.compile(r"^N rows: \d+$")
n_rows_ins = 0 # Rows inserted
n_line = 0 # Position in input file
n_batch = 1

setup_db()

# Table "osm" must exist
osm_table = Table("osm", MetaData(), autoload_with=engine)

for line in fileinput.input():
  line = line.rstrip()
  n_line += 1
  # Get past malformed lines due to printing row counts to stdout in Perl data prep script :-o
  if bad_re.match(line):
    continue
  # 78347 <2018-08-09T22:29:35Z <366321 <63.4305942 <10.3921538 <Prinsenkrysset <highway=traffic_signals|u5r|u5r2|u5r2u|u5r2u7 <u5r2u7pmfxz8b
  a = line.split('<')
  if 8 != len(a):
    continue
  (id, dt, uid, lat, lon, name, kvagg, geohash) = a
  # (lat, lon) may have this format: 54°05.131'..., which is bogus
  if (not llre.match(lat)) or (not llre.match(lon)):
    continue
  # Clean up all the kv data
  kv = []
  # Add the words in the name onto kv
  for w in re.split(r"\W+", name.lower()):
    if len(w) > 0:
      kv.append(w)
  amenity = ""
  search_hints = []
  for x in kvagg.split('|'):
    if len(x) == 0:
      continue;
    x = html.unescape(x)
    x = re.sub(r"['\",{}]", "", x)
    kv.append(x)
    if x.startswith("amenity"):
      amenity = x.split("=")[1]
    # Location details: postcode, street, city
    # Example: addr:postcode=GU27 3HA|addr:street=Midhurst Road
    elif x.startswith("addr:"):
      addr = x.split("=")[1]
      if len(addr) > 0:
        search_hints.append(addr)
  row_map = {
    "geohash4": geohash[:4],
    "amenity": amenity,
    "id": id,
    "date_time": dt,
    "uid": uid,
    "name": html.unescape(name),
    "lat": lat,
    "lon": lon,
    "key_value": kv,
    "search_hints": ' '.join(search_hints)
  }
  rows.append(row_map)
  if len(rows) % rows_per_batch == 0:
    logging.info("Running INSERT for batch %d of %d rows" % (n_batch, rows_per_batch))
    t0 = time.time()
    do_inserts(rows)
    n_rows_ins += rows_per_batch
    rows.clear()
    t1 = time.time()
    logging.info("INSERT for batch %d of %d rows took %.2f s" % (n_batch, rows_per_batch, t1 - t0))
    n_batch += 1

# Last bit
if len(rows) > 0:
  do_inserts(rows)
  n_rows_ins += len(rows)

