-- What are the locations where the tourist can appear?
select * from tourist_locations;

-- Out of these, which have the highest concentrations of pubs?
with a as (
  select geohash4 g4, count(*) n
  from osm
  where
    amenity = 'pub'
    and
    geohash4 in (select substring(geohash, 1, 4) from tourist_locations)
  group by 1
)
select g4, n, array_to_string(array_agg(name), ', ') "place name(s)"
from a, tourist_locations tl
where substring(geohash, 1, 4) = g4
group by g4, n
order by n desc;

-- Find pubs with names containing "Royal" (case insensitive)
select name, lat, lon, st_geohash(st_setsrid(st_makepoint(lon, lat), 4326), 9) gh
from osm
where amenity = 'pub' and name ~* '\bRoyal\b'
order by gh;


