#!/usr/bin/env python3

# $Id: load_geonames.py,v 1.7 2022/09/07 20:41:46 mgoddard Exp mgoddard $

import psycopg2
import psycopg2.errorcodes

import sqlalchemy
from sqlalchemy import create_engine, insert
from sqlalchemy import Table, MetaData

import time
import sys, os
import re
import csv
import logging
import Geohash
from bloom_filter2 import BloomFilter

"""
 $ sudo apt install python3-pip
 $ pip3 install psycopg2-binary
 $ pip3 install sqlalchemy
 $ pip3 install sqlalchemy-cockroachdb
 $ pip3 install bloom-filter2
"""

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p")

#
# Set the following environment variable:
#
#   export DB_URL="postgres://user:passwd@localhost:26257/defaultdb"
#
db_url = os.getenv("DB_URL")
if db_url is None:
  print("Environment DB_URL must be set. Quitting.")
  sys.exit(1)

max_retries = int(os.getenv("MAX_RETRIES", "3"))
logging.info("MAX_RETRIES: {}".format(max_retries))

#
# curl -s -k http://localhost:8000/geonames_osm_eu.tsv.gz | gunzip - | ./load_geonames.py
#

db_url = re.sub(r"^postgres", "cockroachdb", db_url)
logging.info("DB_CONN_STR (rewritten): {}".format(db_url))
engine = create_engine(db_url, pool_pre_ping=True)
logging.info("Engine: OK")

osm_names_table = Table("osm_names", MetaData(), autoload_with=engine)

def do_inserts(list_of_row_maps):
  for retry in range(1, max_retries + 1):
    try:
      with engine.begin() as conn:
        # https://docs.sqlalchemy.org/en/14/tutorial/data_insert.html
        conn.execute(insert(osm_names_table), list_of_row_maps)
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

rows_per_batch = 1024
n_rows_ins = 0 # Rows inserted
n_line = 0 # Position in input file
n_batch = 1
float_re = re.compile(r"^-?\d+\.\d+$")
got_hdr = None

bloom = BloomFilter(max_elements=10500000, error_rate=0.01)
row_list = []
tsv = csv.reader(sys.stdin, delimiter='\t', quotechar='"')
for row in tsv:
  # Skip the header
  if not got_hdr:
    got_hdr = True
    continue
  n_line += 1

  # Verify that columns containing lat / lon values are indeed FLOATs
  floats_ok = True
  for i in (6, 7, 17, 18, 19, 20):
    if not float_re.match(row[i]):
      print("Line {}: failed to match FLOAT '{}'".format(n_line, row[i]))
      floats_ok = False
  if not floats_ok:
    continue

  # Convert any empty string values to None
  for i in range(0, len(row)):
    if len(row[i]) == 0:
      row[i] = None

  geohash = Geohash.encode(float(row[7]), float(row[6]))

  row_map = {
    "name": row[0],
    "alternative_names": row[0] + ' ' + '' if row[1] is None else ' '.join(re.split(r',\s*', row[1])),
    "osm_type": row[2],
    "osm_id": row[3],
    "osm_class": row[4],
    "the_type": row[5],
    "lon": row[6],
    "lat": row[7],
    "place_rank": row[8],
    "importance": row[9],
    "street": row[10],
    "city": row[11],
    "county": row[12],
    "state": row[13],
    "country": row[14],
    "country_code": row[15],
    "display_name": row[16],
    "west": row[17],
    "south": row[18],
    "east": row[19],
    "north": row[20],
    "wikidata": row[21],
    "wikipedia": row[22],
    "geohash5": geohash[:5],
    "geohash6": geohash[:6],
    "geohash7": geohash[:7]
  }

  # Ensure all components of the PK are present
  if row_map["name"] is None or row_map["city"] is None:
    continue

  # Use a Bloom filter keyed by the PK components to avoid dupe rows
  #  PRIMARY KEY (geohash5, geohash7, city, name)
  pk = geohash[:7] + row_map["name"] + row_map["city"]
  if pk in bloom:
    print("{} already seen -- skipping".format(pk))
    continue
  else:
    bloom.add(pk)

  row_list.append(row_map)

  if len(row_list) % rows_per_batch == 0:
    print("Running INSERT for batch %d of %d rows" % (n_batch, rows_per_batch))
    t0 = time.time()
    do_inserts(row_list)
    n_rows_ins += len(row_list)
    row_list.clear()
    t1 = time.time()
    print("INSERT for batch %d of %d rows took %.2f s" % (n_batch, rows_per_batch, t1 - t0))
    n_batch += 1

# Last bit
if len(row_list) > 0:
  do_inserts(row_list)
  n_rows_ins += len(row_list) 

