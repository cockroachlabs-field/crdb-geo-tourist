/*
 * $Id: osm_names.sql,v 1.1 2022/09/08 13:35:20 mgoddard Exp mgoddard $
 */

DROP TABLE IF EXISTS osm_names;
CREATE TABLE osm_names
(
  /*  0 */ name STRING NOT NULL
  /*  1 */, alternative_names STRING
  /*  2 */, osm_type STRING
  /*  3 */, osm_id INT
  /*  4 */, osm_class STRING
  /*  5 */, the_type STRING
  /*  6 */, lon FLOAT NOT NULL
  /*  7 */, lat FLOAT NOT NULL
  /*  8 */, place_rank INT
  /*  9 */, importance FLOAT
  /* 10 */, street STRING
  /* 11 */, city STRING NOT NULL
  /* 12 */, county STRING
  /* 13 */, state STRING
  /* 14 */, country STRING
  /* 15 */, country_code CHAR(2)
  /* 16 */, display_name STRING
  /* 17 */, west FLOAT NOT NULL
  /* 18 */, south FLOAT NOT NULL
  /* 19 */, east FLOAT NOT NULL
  /* 20 */, north FLOAT NOT NULL
  /* 21 */, wikidata STRING
  /* 22 */, wikipedia STRING
  , geohash5 CHAR(5) /* ± 2.4 km */
  , geohash6 CHAR(6) /* ± 610 m */
  , geohash7 CHAR(7) /* ± 76 m */
  , PRIMARY KEY (geohash5, geohash6, geohash7, city, name)
);

