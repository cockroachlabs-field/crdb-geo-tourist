#!/bin/bash

lb_ip=$( kubectl describe service crdb-lb | perl -ne 'chomp; print "$1\n" if /^LoadBalancer Ingress:\s+((\d+\.){3}\d+)/;' )

# Get the CA cert if necessary
[ -f "/tmp/ca.crt" ] || ./get_ca_cert.sh

psql "postgresql://tourist:tourist@${lb_ip}:26257/defaultdb?sslmode=require&sslrootcert=/tmp/ca.crt"

