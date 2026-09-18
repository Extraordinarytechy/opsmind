#!/usr/bin/env bash
# Failure injection for the OpsMind demo loop.
#
# Drives the sample app into an SLO breach so Prometheus fires an alert that OpsMind
# then diagnoses. Two modes:
#   error   - raise the injected error rate (default 0.5 = 50%)
#   latency - add request latency in ms (default 800)
#   podkill - delete a sample-app pod (tests self-healing / restart behaviour)
#   reset   - clear all injected failure
#
# Usage:
#   scripts/inject_failure.sh error 0.6
#   scripts/inject_failure.sh latency 900
#   scripts/inject_failure.sh podkill
#   scripts/inject_failure.sh reset
set -euo pipefail

NS="${NS:-apps}"
MODE="${1:-error}"
VALUE="${2:-}"

svc_url() {
  # Assumes the NodePort mapping from deploy/kind-cluster.yaml.
  echo "http://localhost:30080"
}

case "$MODE" in
  error)
    RATE="${VALUE:-0.5}"
    echo "Injecting error_rate=${RATE} into sample-app ..."
    curl -fsS -X POST "$(svc_url)/chaos?error_rate=${RATE}" && echo
    echo "Generating traffic (200 requests) to trigger the alert ..."
    for _ in $(seq 1 200); do curl -fsS -o /dev/null "$(svc_url)/work" || true; done
    ;;
  latency)
    MS="${VALUE:-800}"
    echo "Injecting extra_latency_ms=${MS} into sample-app ..."
    curl -fsS -X POST "$(svc_url)/chaos?extra_latency_ms=${MS}" && echo
    for _ in $(seq 1 100); do curl -fsS -o /dev/null "$(svc_url)/work" || true; done
    ;;
  podkill)
    echo "Deleting one sample-app pod in namespace ${NS} ..."
    POD="$(kubectl -n "$NS" get pods -l app=sample-app -o jsonpath='{.items[0].metadata.name}')"
    kubectl -n "$NS" delete pod "$POD"
    ;;
  reset)
    echo "Clearing injected failure ..."
    curl -fsS -X POST "$(svc_url)/chaos?error_rate=0&extra_latency_ms=0" && echo
    ;;
  *)
    echo "unknown mode: $MODE (use error|latency|podkill|reset)" >&2
    exit 2
    ;;
esac
