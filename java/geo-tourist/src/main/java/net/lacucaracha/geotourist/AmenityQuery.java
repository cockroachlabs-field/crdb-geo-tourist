package net.lacucaracha.geotourist;

import ch.hsr.geohash.GeoHash;

public class AmenityQuery {

    public AmenityQuery(double lat, double lon, String amenity) {
        this.lat = lat;
        this.lon = lon;
        this.amenity = amenity;
    }

    public AmenityQuery() {
    }

    private double lat;
    private double lon;
    private String amenity;

    public double getLat() {
        return lat;
    }

    public void setLat(double lat) {
        this.lat = lat;
    }

    public double getLon() {
        return lon;
    }

    public void setLon(double lon) {
        this.lon = lon;
    }

    public String getAmenity() {
        return amenity;
    }

    public void setAmenity(String amenity) {
        this.amenity = amenity;
    }

    // https://github.com/kungfoo/geohash-java/blob/master/src/main/java/ch/hsr/geohash/GeoHash.java
    public String getGeohash() {
        return GeoHash.geoHashStringWithCharacterPrecision(lat, lon, 10);
    }

    // TODO: fill this in
    public String toString() {
        return "[lat: " + lat + ", lon:" + lon + ", amenity: " + amenity + "]";
    }
}
