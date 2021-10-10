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
      ST_GeomFromGeoJSON('{"type": "LineString", "coordinates": [[-0.1260852813720703, 51.48838466003402], [-0.12325286865234374, 51.494156298116394], [-0.12187957763671875, 51.50051494213073], [-0.12050628662109375, 51.5058576545476], [-0.11775970458984374, 51.508421934016845], [-0.11338233947753906, 51.50949034120275], [-0.10617256164550781, 51.50997111626239], [-0.09973526000976562, 51.50970401963339], [-0.09312629699707031, 51.50884929989774], [-0.08694648742675781, 51.507941142609155], [-0.0762176513671875, 51.505804230524056]]}')::GEOGRAPHY,
      ref_point, 300, TRUE
    )
    AND amenity = 'pub'
)
SELECT st_asgeojson(pubs)
FROM q1;


