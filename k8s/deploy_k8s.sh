#!/bin/bash

# 4	vCPU, 16 GB RAM, $0.134012/hour
MACHINETYPE="e2-standard-4"
NAME="${USER}-geo-tourist"
ZONE="us-east4-b"
N_NODES=5

# A MapBox "token" is required to show the base map
if [ -z $MAPBOX_TOKEN ]
then
  echo
  echo "Environment variable MAPBOX_TOKEN is not set."
  echo "Please run 'export MAPBOX_TOKEN=\"your.mapbox.token\"' and then try running $0 again."
  echo
  exit 1
fi

dir=$( dirname $0 )
. $dir/include.sh

# 1. Create the GKE K8s cluster
echo "See https://www.cockroachlabs.com/docs/v21.1/orchestrate-cockroachdb-with-kubernetes.html#hosted-gke"
run_cmd gcloud container clusters create $NAME --zone=$ZONE --machine-type=$MACHINETYPE --num-nodes=$N_NODES
if [ "$y_n" = "y" ] || [ "$y_n" = "Y" ]
then
  ACCOUNT=$( gcloud info | perl -ne 'print "$1\n" if /^Account: \[([^@]+@[^\]]+)\]$/' )
  kubectl create clusterrolebinding cluster-admin-binding --clusterrole=cluster-admin --user=$ACCOUNT
fi

# 1. (a) Set current context
kubectl config use-context $NAME

# 2. Create the CockroachDB cluster
echo "See https://www.cockroachlabs.com/docs/stable/deploy-cockroachdb-with-kubernetes.html"
echo "Apply the CustomResourceDefinition (CRD) for the Operator"
run_cmd kubectl apply -f https://raw.githubusercontent.com/cockroachdb/cockroach-operator/v2.4.0/install/crds.yaml

echo "Apply the Operator manifest"
OPERATOR_YAML="https://raw.githubusercontent.com/cockroachdb/cockroach-operator/v2.4.0/install/operator.yaml"
run_cmd kubectl apply -f $OPERATOR_YAML

echo "Setting default namespace to the operator namespace"
run_cmd kubectl config set-context --current --namespace=cockroach-operator-system

echo "Validate that the Operator is running"
run_cmd kubectl get pods

echo "Initialize the cluster"
run_cmd kubectl apply -f ./cockroachdb.yaml

echo "Check that the pods were created"
run_cmd kubectl get pods

echo "WAIT until the output of 'kubectl get pods' shows the three cockroachdb-N nodes in 'Running' state"
run_cmd kubectl get pods

echo "After a couple of minutes, rerun this check"
run_cmd kubectl get pods

echo "Check to see whether the LB for DB Console and SQL is ready yet"
echo "Look for the external IP of the app in the 'LoadBalancer Ingress:' line of output"
run_cmd kubectl describe service crdb-lb
echo "If not, run 'kubectl describe service crdb-lb' in a separate window"

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
echo "Open a browser tab to port 8080 at the IP provided for the DB Console endpoint"
echo "** Use 'tourist' as both login and password **"

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

# 8. Kill a node
echo "Kill a CockroachDB pod"
run_cmd kubectl delete pods cockroachdb-0
echo "Reload the app page to verify it continues to run"
echo "Also, note the state in the DB Console"
echo "A new pod should be started to replace the failed pod"
run_cmd kubectl get pods

# 9. Perform an online rolling upgrade
echo "Perform a zero downtime upgrade of CockroachDB (note the version in the DB Console UI)"
run_cmd kubectl apply -f ./rolling_upgrade.yaml
echo "Check the DB Console to verify the version has changed"
echo

# 10. Tear it down
echo
echo
echo "** Finally: tear it all down.  CAREFUL -- BE SURE YOU'RE DONE! **"
echo "Press ENTER to confirm you want to TEAR IT DOWN."
read
echo "Deleting the Geo Tourist app"
kubectl delete -f ./crdb-geo-tourist.yaml
echo "Deleting the data loader app"
kubectl delete -f ./data-loader.yaml
echo "Deleting the CockroachDB cluster"
kubectl delete -f ./cockroachdb.yaml
echo "Deleting the persistent volumes and persistent volume claims"
kubectl delete pv,pvc --all
echo "Deleting the K8s operator"
kubectl delete -f $OPERATOR_YAML
echo "Deleting the GKE cluster"
gcloud container clusters delete $NAME --zone=$ZONE --quiet

