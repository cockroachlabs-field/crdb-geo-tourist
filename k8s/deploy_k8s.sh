#!/bin/bash

# 4	vCPU, 16 GB RAM, $0.134012/hour
MACHINETYPE="e2-standard-4"
NAME="${USER}-geo-tourist"
ZONE="us-east4-b"
N_NODES=4

function run_cmd {
  cmd="$@"
  echo
  echo "Press ENTER to run \"$cmd\""
  read
  bash -c "$cmd"
  yes '' | sed 3q
}

# Must have a MapBox "token" for this to work
if [ -z $MAPBOX_TOKEN ]
then
  echo
  echo "Environment variable MAPBOX_TOKEN is not set."
  echo "Please run 'export MAPBOX_TOKEN=\"your.mapbox.token\"' and then try running $0 again."
  echo
  exit 1
fi

# 1. Create the GKE K8s cluster
echo "See https://www.cockroachlabs.com/docs/v20.2/orchestrate-cockroachdb-with-kubernetes#hosted-gke"
run_cmd gcloud container clusters create $NAME --zone=$ZONE --machine-type=$MACHINETYPE --num-nodes=$N_NODES

ACCOUNT=$( gcloud info | perl -ne 'print "$1\n" if /^Account: \[([^@]+@[^\]]+)\]$/' )
kubectl create clusterrolebinding cluster-admin-binding --clusterrole=cluster-admin --user=$ACCOUNT

# 2. Create the CockroachDB cluster
echo "See https://www.cockroachlabs.com/docs/v20.2/orchestrate-cockroachdb-with-kubernetes"
echo "Apply the CustomResourceDefinition (CRD) for the Operator"
run_cmd kubectl apply -f https://raw.githubusercontent.com/cockroachdb/cockroach-operator/master/config/crd/bases/crdb.cockroachlabs.com_crdbclusters.yaml

echo "Apply the Operator manifest"
OPERATOR_YAML="https://raw.githubusercontent.com/cockroachdb/cockroach-operator/master/manifests/operator.yaml"
run_cmd kubectl apply -f $OPERATOR_YAML

echo "Validate that the Operator is running"
run_cmd kubectl get pods

echo "Initialize the cluster"
run_cmd kubectl apply -f example.yaml

echo "Check that the pods were created"
run_cmd kubectl get pods

echo "WAIT until the output of 'kubectl get pods' shows the three cockroachdb-N nodes in 'Running' state"
run_cmd kubectl get pods

echo "After a couple of minutes, rerun this check"
run_cmd kubectl get pods

# 3. Add DB user for app
echo "Once all three show 'Running', use the SQL CLI to add a user for use by the Web app"
echo "Press ENTER to run this SQL"
read
cat ./create_user.sql | kubectl exec -i cockroachdb-2 -- ./cockroach sql --certs-dir cockroach-certs

# 4. Create table, index, and load data
echo "Create DB tables and load data (takes about 3 minutes)"
run_cmd kubectl apply -f ./data-loader.yaml
echo "Run 'kubectl get pods' periodically until the line for 'crdb-geo-loader' shows STATUS of 'Completed'"
run_cmd kubectl get pods

# 5. Start the CockroachDB DB Console
LOCAL_PORT=18080
echo "First, set up a tunnel from port $LOCAL_PORT on localhost to port 8080 on one of the CockroachDB pods"
run_cmd nohup kubectl port-forward cockroachdb-1 --address 0.0.0.0 $LOCAL_PORT:8080 >> /tmp/k8s-port-forward.log 2>&1 </dev/null &
URL="http://localhost:$LOCAL_PORT/"
echo "Use 'tourist' as both login and password for this Admin UI"
run_cmd open $URL

# 6. Start the Web app
echo "Press ENTER to start the CockroachDB Geo Tourist app"
read
envsubst < ./crdb-geo-tourist.yaml | kubectl apply -f -

# 7. Get the IP address of the load balancer
run_cmd kubectl describe service crdb-geo-tourist-lb
echo "Look for the external IP of the app in the 'LoadBalancer Ingress:' line of output"
sleep 30
run_cmd kubectl describe service crdb-geo-tourist-lb
echo "Once that IP is available, open the URL http://THIS_IP/ to see the app running"
echo
echo "Finally: tear it all down.  CAREFUL -- BE SURE YOU'RE DONE!"
echo "Press ENTER to confirm you want to TEAR IT DOWN."
read
run_cmd kubectl delete -f ./crdb-geo-tourist.yaml
run_cmd kubectl delete -f ./data-loader.yaml
run_cmd kubectl delete -f example.yaml
run_cmd kubectl delete pv,pvc --all
run_cmd kubectl delete -f $OPERATOR_YAML
run_cmd gcloud container clusters delete $NAME --zone=$ZONE --quiet

