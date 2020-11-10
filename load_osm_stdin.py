#!/usr/bin/env python3

import psycopg2
import psycopg2.errorcodes
import time
import sys, os
import gzip
import html
import re
import fileinput

#
# Set the following environment variables, or use the PostgreSQL defaults:
# PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE
#
# curl -s -k http://localhost:8000/osm_1m_eu.txt.gz | gunzip - | ./load_osm_stdin.py
#

rows_per_batch = 10000 # Edit as necessary, but 10k rows is a good starting point

conn = None
def get_db():
  global conn
  if conn is None:
    conn = psycopg2.connect(
      database=os.getenv("PGDATABASE", "defaultdb")
      , user=os.getenv("PGUSER", "root")
      , port=int(os.getenv("PGPORT", "26257"))
      , host=os.getenv("PGHOST", "localhost")
      , application_name="OSM Data Loader"
    )
  return conn

def close_db():
  global conn
  if conn is not None:
    conn.close()
    conn = None

def insert_row(sql, close=False):
  conn = get_db()
  with conn.cursor() as cur:
    try:
      cur.execute(sql)
      #n_ins = cur.rowcount
    except Exception as e:
      print("execute(sql): ", e)
      sys.exit(1)
  try:
    conn.commit()
  except Exception as e:
    print("commit(): ", e)
    print("Retrying commit() in 1 s")
    time.sleep(1)
    conn.commit()
  if close:
    close_db()

"""
CREATE TABLE osm
(
  id BIGINT
  , date_time TIMESTAMP WITH TIME ZONE
  , uid TEXT
  , name TEXT
  , key_value TEXT[]
  , ref_point GEOGRAPHY
  , geohash4 TEXT -- first N chars of geohash (here, 4 for box of about +/- 20 km)
  , CONSTRAINT "primary" PRIMARY KEY (geohash4 ASC, id ASC)
);
"""

sql = "INSERT INTO osm (id, date_time, uid, name, key_value, ref_point, geohash4) VALUES "

vals = []
llre = re.compile(r"^-?\d+\.\d+$")
bad_re = re.compile(r"^N rows: \d+$")
n_rows_ins = 0 # Rows inserted
n_line = 0 # Position in input file
n_batch = 1

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
  row = str(id) + ", '" + dt + "', '" + uid + "', '" + html.unescape(name).replace("'", "''") + "'"
  # Clean up all the kv data
  kv = []
  # Add the words in the name onto kv
  for w in re.split(r"\W+", name.lower()):
    if len(w) > 0:
      kv.append(w)
  for x in kvagg.split('|'):
    if len(x) == 0:
      continue;
    x = html.unescape(x)
    x = re.sub(r"['\",{}]", "", x)
    kv.append(x)
  row += ", '{" + ','.join(kv) + "}'"
  row += ", ST_MakePoint(" + lon + ", " + lat + ")::GEOGRAPHY, '" + geohash[0:4] + "'"
  vals.append("(" + row + ")")
  if len(vals) % rows_per_batch == 0:
    print("Running INSERT for batch %d of %d rows" % (n_batch, rows_per_batch))
    t0 = time.time()
    insert_row(sql + ', '.join(vals))
    n_rows_ins += rows_per_batch
    vals.clear()
    t1 = time.time()
    print("INSERT for batch %d of %d rows took %.2f s" % (n_batch, rows_per_batch, t1 - t0))
    n_batch += 1

# Last bit
if len(vals) > 0:
  insert_row(sql + ', '.join(vals))
  n_rows_ins += rows_per_batch

close_db()

