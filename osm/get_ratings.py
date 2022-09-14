#!/usr/bin/env python3

"""
 Ratings are from TripAdvisor, provided by Bing

 https://www.crummy.com/software/BeautifulSoup/bs4/doc/

 $ pip3 install beautifulsoup4
 $ pip3 install requests

 $Id: get_ratings.py,v 1.2 2022/09/12 00:11:35 mgoddard Exp mgoddard $

"""

from bs4 import BeautifulSoup
import urllib.parse
import requests
import re
import sys

if len(sys.argv) < 2:
  print("Usage: {} search terms ...".format(sys.argv[0]))
  sys.exit(1)

rating_re = re.compile(r"Star Rating: (\d(.\d)?) out of 5.")

q = ' '.join(sys.argv[1:])

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
    print("Rating: {}".format(mat.group(1)))
else:
  print("No match for '{}'".format(q))

