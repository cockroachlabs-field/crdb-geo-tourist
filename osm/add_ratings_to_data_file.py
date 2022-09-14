#!/usr/bin/env python3

"""
 Ratings are from TripAdvisor, provided by Bing

 https://www.crummy.com/software/BeautifulSoup/bs4/doc/

 $ pip3 install beautifulsoup4
 $ pip3 install requests

 $Id: get_ratings.py,v 1.2 2022/09/12 00:11:35 mgoddard Exp mgoddard $

"""

N_COLS = 8

from bs4 import BeautifulSoup
import urllib.parse
import requests
import re
import sys
import fileinput
import datetime
import html

rating_re = re.compile(r"Star Rating: (\d(.\d)?) out of 5.")
addr_pat = re.compile(r"^addr:(?:city|postcode|street)=(.+)$")

# Given an array of query terms, return the FLOAT value of its rating (1 - 5).
def get_rating(query_terms):
  q = ' '.join(query_terms)
  rv = None
  # FIXME: This doesn't properly deal with "Арома Кава Kyiv", for example
  q = urllib.parse.quote_plus(q)
  hdr = {
      "User-Agent": "Mozilla/5.0 (Android 4.4; Mobile; rv:41.0) Gecko/41.0 Firefox/41.0"
  }
  url = "https://www.bing.com/search?q="
  r = requests.get(url + q, headers=hdr)
  #print(r.text)
  """
  Bing results:
  <span class="csrc sc_rc1" role="img" aria-label="Star Rating: 4.5 out of 5.">
  """
  bs = BeautifulSoup(r.text, features="html.parser")
  ratings = bs.findAll("span", {"class": "csrc sc_rc1"})
  if ratings is not None and len(ratings) > 0:
    rating = ratings[0]['aria-label'] # Star Rating: 4.5 out of 5.
    #print(rating)
    mat = rating_re.match(rating)
    if mat is not None:
      rv = mat.group(1)
  return rv

for line in fileinput.input():
  line = line.rstrip()
  a = line.split('<')
  if N_COLS != len(a):
    continue
  (id, dt, uid, lat, lon, name, kvagg, geohash) = a
  terms = [name]
  # Only need name and kvagg
  for x in kvagg.split('|'):
    if len(x) == 0:
      continue;
    x = html.unescape(x)
    x = re.sub(r"['\",{}]", "", x)
    m = addr_pat.match(x)
    if m is not None:
      terms.append(m.group(1))
  rating = get_rating(terms)
  if rating is not None:
    a.append(rating)
    a.append(datetime.datetime.now().isoformat())
  else:
    a.append("")
    a.append("")
  print('<'.join(a))

