# Common definitions

function run_cmd {
  cmd="$@"
  echo
  read -p "Type 'Y' ENTER to run \"$cmd\": " y_n
  y_n=${y_n:-N}
  case $y_n in
    ([yY])
      bash -c "$cmd"
      ;;
    (*)
      echo "Skipping"
      ;;
  esac
  yes '' | sed 3q
}

LOCAL_PORT=18080
ADMIN_UI_NODE="cockroachdb-2"

function port_fwd {
  for pid in $( ps -ef | grep port-forward | grep -v grep | awk '{print $2}' )
  do
    kill $pid && echo "Killed $pid"
  done
  nohup kubectl port-forward $ADMIN_UI_NODE --address 0.0.0.0 $LOCAL_PORT:8080 >> /tmp/k8s-port-forward.log 2>&1 </dev/null &
  nohup kubectl port-forward $ADMIN_UI_NODE --address 0.0.0.0 5432:26257 >> /tmp/k8s-5432-forward.log 2>&1 </dev/null &
}

