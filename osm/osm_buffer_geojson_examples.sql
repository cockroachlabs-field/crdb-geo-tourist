/*

 Sara Cafe Shisha                  | (51.5200399, -0.1586635) | cafe            | gcpvh6
 The Queen's Head                  | (51.5284524, -0.1181488) | pub             | gcpvjk
 Jacob the Angel                   | (51.5143804, -0.1261664) | cafe            | gcpvj1
 Islington and Finsbury Youth Club | (51.5300711, -0.1048182) | public_building | gcpvjs
 Gail's Bakery                     | (51.5620676, -0.1494459) | cafe            | gcpvkd
 Mill Hill Tandoori                | (51.6139332, -0.2487185) | restaurant      | gcpvdk

 */

select
  name
  , '(' || ST_Y(ref_point::GEOMETRY)::text || ', ' || ST_X(ref_point::GEOMETRY)::text || ')' latlon
  , amenity
  , key_value[array_upper(key_value, 1)]
from osm
where geohash4 = 'gcpv'i
order by random() asc
limit 20;

/*

A line along the Thames in London:

  select ST_LineFromText('LineString(-0.11591719035390817 51.50904688102181, -0.08686350483840344 51.50776477693785)')::GEOGRAPHY;

 */

/* Search for pubs within a 500m buffer along a section of the River Thames in London */
WITH q1 AS
(
  SELECT
    name
    , amenity
    , ST_Y(ref_point::GEOMETRY) lat
    , ST_X(ref_point::GEOMETRY) lon
  FROM osm
  WHERE
    ST_DWithin
    (
      ST_LineFromText('LineString(-0.11591719035390817 51.50904688102181, -0.08686350483840344 51.50776477693785)')::GEOGRAPHY,
      ref_point, 500, TRUE
    )
    AND amenity = 'pub'
)
SELECT name, amenity, '(' || lat::TEXT || ', ' || lon::TEXT || ')' latlon
FROM q1
ORDER BY lon ASC, lat ASC;

/* Same as above, but extract locations as GeoJSON and then paste into https://geojson.io/ */
WITH q1 AS
(
  SELECT
    st_collect(ref_point::geometry) as pubs
  FROM osm
  WHERE
    ST_DWithin
    (
      ST_LineFromText('LineString(-0.11591719035390817 51.50904688102181, -0.08686350483840344 51.50776477693785)')::GEOGRAPHY,
      ref_point, 500, TRUE
    )
    AND amenity = 'pub'
)
SELECT st_asgeojson(pubs)
FROM q1;

/* Similar, but starting with GeoJSON generated from the UI provided by https://geojson.io/ */
WITH q1 AS
(
  SELECT
    st_collect(ref_point::geometry) as pubs
  FROM osm
  WHERE
    ST_DWithin
    (
      ST_GeomFromGeoJSON('{"type":"LineString","coordinates":[[-0.16908645629882812,51.48191741979991],[-0.15672683715820312,51.48373475351443],[-0.14848709106445312,51.484696842043554],[-0.1373291015625,51.48384165324227],[-0.12874603271484375,51.48651406499528],[-0.12462615966796874,51.49025517833077],[-0.12325286865234374,51.4936753561844],[-0.12256622314453125,51.49795021767351],[-0.12102127075195312,51.503400084633526],[-0.1187896728515625,51.50756719022885],[-0.11278152465820314,51.50959718054333],[-0.09647369384765625,51.50938350161162],[-0.08960723876953125,51.50799456412721],[-0.08136749267578125,51.50713981232172],[-0.0734710693359375,51.50489601254001],[-0.06832122802734375,51.503186376638006],[-0.06196975708007812,51.50190410761811],[-0.05390167236328125,51.50329323076107],[-0.05115509033203125,51.50500286265417],[-0.045833587646484375,51.50799456412721]]}')::GEOGRAPHY,
      ref_point, 300, TRUE
    )
    AND amenity = 'pub'
)
SELECT st_asgeojson(pubs)
FROM q1;

/* Contrast the above result with this one, a point/radius query */
WITH q1 AS
(
  SELECT
    st_collect(ref_point::geometry) as pubs
  FROM osm
  WHERE
    ST_DWithin
    (
      ST_MakePoint(-0.099281, 51.508337)::GEOGRAPHY,
      ref_point, 5.0E+03, TRUE
    )
    AND amenity = 'pub'
)
SELECT st_asgeojson(pubs)
FROM q1;

/* Find pubs along the route from Paddington Station to Tower Bridge area */
WITH q1 AS
(
  SELECT
    st_collect(ref_point::geometry) as pubs
  FROM osm
  WHERE
    ST_DWithin
    (
      ST_GeomFromGeoJSON('{"type":"LineString","coordinates":[[-0.07604598999023438,51.50927666176991],[-0.17560958862304688,51.51664802308175]]}')::GEOGRAPHY,
      ref_point, 500, TRUE
    )
    AND amenity = 'pub'
)
SELECT st_asgeojson(pubs)
FROM q1;

