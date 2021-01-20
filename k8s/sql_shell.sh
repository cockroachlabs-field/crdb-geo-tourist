#!/bin/bash

kubectl exec --stdin --tty cockroachdb-2 -- cockroach sql --certs-dir=./cockroach-certs

