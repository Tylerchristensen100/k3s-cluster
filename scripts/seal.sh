#!/usr/bin/env bash
# Seal a secret offline from any machine using the committed PUBLIC cert (no cluster access needed).
# Usage: scripts/seal.sh <namespace> <secret-name> <out-file> KEY=VALUE [KEY=VALUE ...]
#        scripts/seal.sh <namespace> <secret-name> <out-file> KEY=@path/to/file
# Values are read via kubectl's --from-literal/--from-file; they never touch disk in plain text.
set -euo pipefail
[ $# -ge 4 ] || { sed -n '2,5p' "$0"; exit 1; }
ns=$1 name=$2 out=$3; shift 3
cert="$(dirname "$0")/../certs/sealed-secrets-pub.pem"
args=()
for kv in "$@"; do
  k=${kv%%=*} v=${kv#*=}
  case $v in @*) args+=(--from-file="$k=${v#@}");; *) args+=(--from-literal="$k=$v");; esac
done
kubectl create secret generic "$name" -n "$ns" --dry-run=client -o yaml "${args[@]}" \
  | kubeseal --cert "$cert" --scope strict -o yaml > "$out"
echo "wrote $out"
