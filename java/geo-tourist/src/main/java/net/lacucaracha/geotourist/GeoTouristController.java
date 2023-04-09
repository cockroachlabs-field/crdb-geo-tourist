package net.lacucaracha.geotourist;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

@RestController
public class GeoTouristController {

    @Autowired
    JdbcTemplate jdbcTemplate;

    // Whether to use the geohash form of the SQL query
    static boolean useGeohash = true;

    static {
        String useGeohashStr = System.getenv("USE_GEOHASH");
        if (useGeohashStr != null && "false".equals(useGeohashStr.toLowerCase(Locale.ROOT))) {
            useGeohash = false;
        }
    }

    // https://docs.spring.io/spring-framework/docs/3.0.x/spring-framework-reference/html/jdbc.html
    @GetMapping("/sites")
    public LatLon getSite() {
        String sql = "SELECT lat, lon\n" +
                "  FROM tourist_locations\n" +
                "  WHERE enabled = TRUE\n" +
                "  ORDER BY RANDOM()\n" +
                "  LIMIT 1;";
        LatLon latLon;
        try {
            latLon = jdbcTemplate.queryForObject(sql, new RowMapper<LatLon>() {
                        public LatLon mapRow(ResultSet rs, int rowNum) throws SQLException {
                            LatLon rv = new LatLon();
                            rv.setLat(rs.getDouble("lat"));
                            rv.setLon(rs.getDouble("lon"));
                            return rv;
                        }
                    }
            );
        } catch (EmptyResultDataAccessException e) { // Not likely
            latLon = new LatLon(51.506712, -0.127235);
        }
        return latLon;
    }

    @PostMapping(value = "/features", consumes = "application/json", produces = "application/json")
    public List<Amenity> getFeatures(@RequestBody AmenityQuery amenityQuery) {
        // FIXME
        System.out.println(amenityQuery.toString());
        List<Amenity> rv = new ArrayList<>();
        String sql = "WITH q1 AS\n" +
                "  (\n" +
                "    SELECT\n" +
                "      name,\n" +
                "      ST_Distance(ST_MakePoint(?, ?)::GEOGRAPHY, ref_point)::NUMERIC(9, 2) dist_m,\n" +
                "      ST_Y(ref_point::GEOMETRY) lat,\n" +
                "      ST_X(ref_point::GEOMETRY) lon,\n" +
                "      date_time,\n" +
                "      key_value,\n" +
                "      rating\n" +
                "    FROM osm\n" +
                "    WHERE\n";
        if (useGeohash) {
            sql += "geohash4 = SUBSTRING(? FOR 4) AND amenity = ?\n";
        } else {
            sql += "ST_DWithin(ST_MakePoint(?, ?)::GEOGRAPHY, ref_point, 5.0E+03, TRUE)\n";
            sql += "AND key_value && ARRAY[?]\n";
        }
        sql += ")\n" +
                "SELECT * FROM q1\n";
        if (useGeohash) {
            sql += "WHERE dist_m < 5.0E+03\n";
        }
        sql += "ORDER BY dist_m ASC\n" +
                "  LIMIT 10;";

        double lat = amenityQuery.getLat();
        double lon = amenityQuery.getLon();
        String amenityType = amenityQuery.getAmenity();
        String geohash = amenityQuery.getGeohash();
        rv = this.jdbcTemplate.query(
                sql,
                (useGeohash ? new Object[]{lon, lat, geohash, amenityType} : new Object[]{lon, lat, lon, lat, amenityType}),
                new RowMapper<Amenity>() {
                    public Amenity mapRow(ResultSet rs, int rowNum) throws SQLException {
                        Amenity amenity = new Amenity();
                        amenity.setName(rs.getString("name"));
                        amenity.setAmenity(amenityType);
                        amenity.setDist_m(rs.getDouble("dist_m"));
                        amenity.setLat(rs.getDouble("lat"));
                        amenity.setLon(rs.getDouble("lon"));
                        Double rating = rs.getDouble("rating");
                        if (rating == null) {
                            amenity.setRating("(not rated)");
                        } else {
                            amenity.setRating("Rating: " + rating + " out of 5");
                        }
                        return amenity;
                    }
                });
        return rv;
    }

}
