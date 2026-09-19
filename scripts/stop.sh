#!/usr/bin/env bash
# Stop whatever is serving the PathLens ports (demo app :4173, backend :8000).
set -uo pipefail
for port in 8000 4173; do
  pids=$(ss -ltnpH "sport = :$port" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null && echo "stopped :$port (pid $pids)"
  else
    echo ":$port not running"
  fi
done
