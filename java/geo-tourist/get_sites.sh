#!/bin/bash

. ./env.sh

curl http://localhost:${FLASK_PORT}/sites | jq

