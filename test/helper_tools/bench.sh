#!/usr/bin/env bash

kill -s KILL $(pidof caddy)

caddy file-server -listen 127.0.0.1:8000 &

benchit() {
  kill -s KILL $(pidof python3)
  mitmdump -q &
  sleep 10
  echo "bench..."
  hey -x http://127.0.0.1:8080 -n 2000 -disable-keepalive http://127.0.0.1:8000/bench.sh
}

for i in {1..2} ; do
  git stash -q
  benchit
  echo "^ without changes"

  git stash pop -q
  benchit
  echo "^ with changes"
done

kill -s KILL $(pidof caddy)
kill -s KILL $(pidof python3)
