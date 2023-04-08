package net.lacucaracha.geotourist;

public class Amenity {

    private String name;
    private String amenity;
    private double dist_m;
    private double lat;
    private double lon;
    private String rating;

    public Amenity() {
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getAmenity() {
        return amenity;
    }

    public void setAmenity(String amenity) {
        this.amenity = amenity;
    }

    public double getDist_m() {
        return dist_m;
    }

    public void setDist_m(double dist_m) {
        this.dist_m = dist_m;
    }

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

    public String getRating() {
        return rating;
    }

    public void setRating(String rating) {
        this.rating = rating;
    }
}
