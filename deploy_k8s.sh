#!/bin/bash

# 2 vCPU, 8 GB RAM, $0.075462/hour
MACHINETYPE="e2-standard-2"
NAME="${USER}-geo-tourist"
ZONE="us-east4-b"

# Create the GKE K8s cluster
gcloud container clusters create $NAME --zone=$ZONE --machine-type=$MACHINETYPE --num-nodes=4

ACCOUNT=$( gcloud info | perl -ne 'print "$1\n" if /^Account: \[([^@]+@[^\]]+)\]$/' )

kubectl create clusterrolebinding cluster-admin-binding --clusterrole=cluster-admin --user=$ACCOUNT

# Create the CockroachDB cluster
YAML="https://raw.githubusercontent.com/cockroachdb/cockroach/master/cloud/kubernetes/cockroachdb-statefulset.yaml"
kubectl apply -f $YAML

# Initialize DB / cluster
YAML="https://raw.githubusercontent.com/cockroachdb/cockroach/master/cloud/kubernetes/cluster-init.yaml"
kubectl apply -f $YAML

# Create table, index, and load data
YAML="./data-loader.yaml"
kubectl apply -f $YAML

# Start the Web UI
YAML="./crdb-geo-tourist.yaml"
kubectl apply -f $YAML

