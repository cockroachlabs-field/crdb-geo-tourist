#!/bin/bash

curl --header "Content-Type: application/json" --request POST --data '{ "lat": 51.506712, "lon": -0.127235, "amenity": "pub" }' http://localhost:8081/features | jq

