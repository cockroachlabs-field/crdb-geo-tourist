#!/usr/bin/env perl

use strict;
use Geo::Hash;
 
my $num_to_find = 100_000_000;

my $col_sep = "<"; # Illegal in the XML, so safe to use as delimiter
my @col_names = qw( id timestamp uid lat lon name key_value );
my %cols = ();
$/  = "</node>\n";

sub reset_cols {
  %cols = map { $_ => undef } @col_names;
}

# - Get a line, a "...</node>", look for leading "<node [^/]+?>", parse it.
# - Split the remainder on the "\n", looking at each "<tag ..>", to fill %col.
# - Only print the result if the place has a name.
# - Any other "<tag ..." data will be placed in final column, "key_value": k1=v1|k2=v2|...

reset_cols();
my $num_found = 0;
my $gh = Geo::Hash->new;
while (<>)
{
  last if $num_found >= $num_to_find;
  my $geohash = "";
  if (/<node +id="(\d+)" +version="\d+" +timestamp="([^"]+)" +uid="(\d+)" +user="[^"]+" +changeset="\d+" +lat="([^"]+)" +lon="([^"]+)">/) {
    $cols{id} = $1;
    $cols{timestamp} = $2;
    $cols{uid} = $3;
    $cols{lat} = $4;
    $cols{lon} = $5;
    my $lat_lon = join(',', $4, $5);
    $geohash = $gh->encode($cols{lat}, $cols{lon});

    my @key_value = ();
    foreach my $tag (split /\n/)
    {
      if ($tag =~ m~<tag +k="([^"]+)" v="([^"]+)"\s*/>~) {
        if (exists $cols{$1}) {
          $cols{$1} = $2;
        } else {
          (my $k = $1) =~ s/[\|=]/~/g;
          (my $v = $2) =~ s/[\|=]/~/g;
          push @key_value, $k . "=" . $v;
        }
      }
    }
    # Append a few geohash substrings
    for (my $i = 3; $i < 7; $i++)
    {
      push(@key_value, substr($geohash, 0, $i));
    }
    $cols{key_value} = join("|", @key_value);
  }
  if ($cols{name}) {
    $num_found += 1;
    print join($col_sep, @cols{@col_names}, $geohash) . "\n";
    print STDERR "N rows: $num_found\n" if $num_found % 1000 == 0;
  }
  reset_cols();
}

__DATA__
<node id="271251" version="4" timestamp="2009-09-09T22:16:06Z" uid="169366" user="Tunafish" changeset="2430548" lat="50.8052" lon="-1.67253">
    <tag k="name" v="Station House"/>
    <tag k="amenity" v="restaurant"/>
    <tag k="cuisine" v="tea;restaurant"/>
</node>
<node id="4082701" version="4" timestamp="2013-10-22T06:40:09Z" uid="453141" user="ppr9" changeset="18480867" lat="52.1602045" lon="-0.4921953">
    <tag k="name" v="Bellini&apos;s"/>
    <tag k="amenity" v="restaurant"/>
    <tag k="wheelchair" v="yes"/>
    <tag k="addr:street" v="High Street"/>
    <tag k="addr:postcode" v="MK41 6EG"/>
    <tag k="addr:housenumber" v="44,46"/>
</node>

