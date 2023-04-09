#!/bin/bash

. ./docker_include.sh

docker build -t $docker_id/$img_name .

