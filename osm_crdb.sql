/*

Build Tag:        v20.2.0-rc.3
Build Time:       2020/10/26 19:07:17
Distribution:     CCL
Platform:         darwin amd64 (x86_64-apple-darwin14)
Go Version:       go1.13.14
C Compiler:       4.2.1 Compatible Clang 3.8.0 (tags/RELEASE_380/final)
Build Commit ID:  d67a35edddabcdd18954196a5e20bfd2a55a27e4
Build Type:       release

Tests were run on a MacBook Pro:
  2 GHz Quad-Core Intel Core i5
  32 GB 3733 MHz LPDDR4X
  1 TB SSD

 */

-- Table for querying an extract of Open Street Map "Planet" dump
DROP TABLE IF EXISTS osm;
CREATE TABLE osm
(
  id BIGINT
  , date_time TIMESTAMP WITH TIME ZONE
  , uid TEXT
  , name TEXT
  , key_value TEXT[]
  , ref_point GEOGRAPHY
  , geohash4 TEXT -- First 4 characters of geohash, corresponding to a box of about +/- 20 km
  , CONSTRAINT "primary" PRIMARY KEY (geohash4 ASC, id ASC)
);

-- I1: Time to load 1M rows with only the primary index is 1:45 (1 minute, 45 seconds)
-- NOTE: In all cases, the INSERTs were done in batches of 10k rows

-- I2: Create index on the GEOGRAPHY column
-- Time to load 1M rows with the primary index plus this GIN index is 5:20
CREATE INDEX ON osm USING GIN(ref_point);

-- I3: Create index on the key_value column, an array of TEXT
-- Time to load 1M rows with the primary index plus this GIN index is 24:21
CREATE INDEX ON osm USING GIN(key_value);

-- Q1: use a geohash substring, part of the PK, coupled with a distance calculation
-- Runtime is ~ 40 ms
-- Uses I1
WITH q1 AS
(
  SELECT name,
    ST_Distance(ST_MakePoint(-0.127235, 51.506712)::GEOGRAPHY, ref_point)::NUMERIC(9, 2) dist_m,
    CONCAT('(', ST_Y(ref_point::GEOMETRY)::STRING, ', ', ST_X(ref_point::GEOMETRY)::STRING, ')') "(lat, lon)",
    geohash4, date_time, key_value
  FROM osm
  WHERE
    geohash4 = SUBSTRING('gcpvj0e275n8' FOR 4)
    AND key_value && '{amenity=pub, real_ale=yes}'
)
SELECT * FROM q1
WHERE dist_m < 5.0E+03
ORDER BY dist_m ASC
LIMIT 10;

-- Q2: use ST_DWithin, which will use the GIN index on the GEOGRAPHY column
-- Runtime is ~ 220 ms
-- Uses I2
WITH q2 AS
(
  SELECT name,
    ST_Distance(ST_MakePoint(-0.127235, 51.506712)::GEOGRAPHY, ref_point)::NUMERIC(9, 2) dist_m,
    CONCAT('(', ST_Y(ref_point::GEOMETRY)::STRING, ', ', ST_X(ref_point::GEOMETRY)::STRING, ')') "(lat, lon)",
    geohash4, date_time, key_value
  FROM osm
  WHERE
    ST_DWithin(ST_MakePoint(-0.127235, 51.506712)::GEOGRAPHY, ref_point, 5.0E+03, TRUE)
    AND key_value && '{amenity=pub, real_ale=yes}'
)
SELECT * FROM q2
ORDER BY dist_m ASC
LIMIT 10;

-- Q3: use a single GIN index on the key_value array, which incorporates a substring of the geohash
-- Runtime varies from 40 ms to 240 ms, depending on the length of the geohash substring in the predicate
-- Runtime using the 4 character geohash is ~ 180 ms
-- Uses I3
WITH q3 AS
(
  SELECT name,  -- Full geohash: gcpvj8zdq58v
    ST_Distance(ST_MakePoint(-0.099305, 51.508432)::GEOGRAPHY, ref_point::GEOGRAPHY)::NUMERIC(9, 2) dist_m,
    CONCAT('(', ST_Y(ref_point::GEOMETRY)::STRING, ', ', ST_X(ref_point::GEOMETRY)::STRING, ')') "(lat, lon)",
    date_time, uid, key_value
  FROM osm
  WHERE
    key_value @> '{gcpv, amenity=pub, real_ale=yes}'
)
SELECT * FROM q3
-- AS OF SYSTEM TIME experimental_follower_read_timestamp()
WHERE dist_m < 5.0E+03
ORDER BY dist_m ASC
LIMIT 10;

/*
 Find coordinates of 1.2 km boxes having highest density of pubs within the 40 km box corresponding
 to the "gcpv" geohash substring used in the WHERE clause.
 (last element of the key_value array is the 6-character substring of the geohash)
 Runtime is ~ 2.25 seconds
*/
WITH p AS
(
  SELECT key_value[ARRAY_LENGTH(key_value, 1)] box
    , ST_PointFromGeoHash(key_value[ARRAY_LENGTH(key_value, 1)]) pt
    , COUNT(*) n_pubs
  FROM osm
  WHERE key_value @> '{gcpv, amenity=pub}'
  GROUP BY 1, 2
  ORDER BY 3 DESC
  LIMIT 10
)
SELECT box "1.2 km box"
  , '(' || ST_Y(pt)::STRING || ', ' || ST_X(pt)::STRING || ')' "(lat, lon)"
  , n_pubs "number of pubs"
FROM p;

