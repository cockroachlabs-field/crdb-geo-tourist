/* v1: using the single geohash column */
WITH a AS
(
  SELECT UNNEST(STRING_TO_ARRAY(LOWER(name) || ' ' || LOWER(city), ' ')) term
  FROM osm_names
  WHERE geohash = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 7)
)
SELECT ARRAY_TO_STRING(ARRAY_AGG(DISTINCT term), ' ')
FROM a;

/* v2: using multiple geohash columns */
WITH a AS
(
  SELECT UNNEST(STRING_TO_ARRAY(LOWER(name) || ' ' || LOWER(city), ' ')) term
  FROM osm_names
  WHERE
    geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
    AND geohash7 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 7)
)
SELECT ARRAY_TO_STRING(ARRAY_AGG(DISTINCT term), ' ')
FROM a;

/* v3: Adding a COALESCE for when the geohash7 constraint finds nothing. */
SELECT COALESCE (
  (WITH a AS (
    SELECT UNNEST(STRING_TO_ARRAY(LOWER(name) || ' ' || LOWER(city), ' ')) term
    FROM osm_names
    WHERE
      geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
      AND geohash7 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 7)
  )
  SELECT ARRAY_TO_STRING(ARRAY_AGG(DISTINCT term), ' ')
  FROM a),
  (WITH b AS (
    SELECT UNNEST(STRING_TO_ARRAY(LOWER(city), ' ')) term
    FROM osm_names
    WHERE
      geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
  )
  SELECT ARRAY_TO_STRING(ARRAY_AGG(DISTINCT term), ' ')
  FROM b)
);

/* v4: fix the issue with too many terms for "city" */
SELECT COALESCE (
  (WITH a AS (
    SELECT UNNEST(STRING_TO_ARRAY(LOWER(name) || ' ' || LOWER(city), ' ')) term
    FROM osm_names
    WHERE
      geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
      AND geohash7 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 7)
  )
  SELECT ARRAY_TO_STRING(ARRAY_AGG(DISTINCT term), ' ')
  FROM a),
  (WITH b AS (
    SELECT UNNEST(STRING_TO_ARRAY(LOWER(city), ' ')) term, COUNT(*)
    FROM osm_names
    WHERE geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
    GROUP BY term
    ORDER BY 2 DESC
    LIMIT 1
  )
  SELECT term
  FROM b)
);

/*
  The idea is to take the terms resulting from this query, combine with the
  amenity type and the name of the place, then query Google to get reviews.
 */
SELECT COALESCE (
  (WITH a AS (
    SELECT UNNEST(STRING_TO_ARRAY(LOWER(name) || ' ' || LOWER(city), ' ')) term, COUNT(*)
    FROM osm_names
    WHERE
      geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
      AND geohash7 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 7)
    GROUP BY term
    ORDER BY 2 DESC
    LIMIT 2
  )
  SELECT ARRAY_TO_STRING(ARRAY_AGG(DISTINCT term), ' ')
  FROM a),
  (WITH b AS (
    SELECT UNNEST(STRING_TO_ARRAY(LOWER(city), ' ')) term, COUNT(*)
    FROM osm_names
    WHERE geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
    GROUP BY term
    ORDER BY 2 DESC
    LIMIT 1
  )
  SELECT term
  FROM b)
);

/* Add a geohash6 (± 610 m) to the PK */
SELECT COALESCE (
  (WITH a AS (
    SELECT UNNEST(STRING_TO_ARRAY(LOWER(name) || ' ' || LOWER(city), ' ')) term, COUNT(*)
    FROM osm_names
    WHERE
      geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
      AND geohash6 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 6)
      AND geohash7 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 7)
    GROUP BY term
    ORDER BY 2 DESC
    LIMIT 4
  )
  SELECT ARRAY_TO_STRING(ARRAY_AGG(term), ' ')
  FROM a),
  (WITH b AS (
    SELECT UNNEST(STRING_TO_ARRAY(LOWER(name) || ' ' || LOWER(city), ' ')) term, COUNT(*)
    FROM osm_names
    WHERE
      geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
      AND geohash6 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 6)
    GROUP BY term
    ORDER BY 2 DESC
    LIMIT 4
  )
  SELECT ARRAY_TO_STRING(ARRAY_AGG(term), ' ')
  FROM b),
  (WITH c AS (
    SELECT UNNEST(STRING_TO_ARRAY(LOWER(city), ' ')) term, COUNT(*)
    FROM osm_names
    WHERE geohash5 = ST_GeoHash(ST_SetSRID(ST_Point(:lon, :lat), 4326), 5)
    GROUP BY term
    ORDER BY 2 DESC
    LIMIT 1
  )
  SELECT ARRAY_TO_STRING(ARRAY_AGG(term), ' ')
  FROM c)
);

