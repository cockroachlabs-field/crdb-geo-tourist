#!/bin/bash

kubectl exec -i cockroachdb-client-secure -- /bin/bash -c "cat cockroach-certs/ca.crt" > /tmp/ca.crt

