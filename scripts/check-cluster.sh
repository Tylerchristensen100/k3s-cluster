#!/usr/bin/env bash
# Read-only live health check of the k3s-node cluster. Changes nothing.
#
# Run on the node:     bash scripts/check-cluster.sh
# From your PC (bash): ssh k3s-node@192.168.0.246 'bash -s' < scripts/check-cluster.sh
# From PowerShell:     Get-Content scripts\check-cluster.sh -Raw | ssh k3s-node@192.168.0.246 'bash -s'
# Exit code: 0 = all checks passed, 1 = at least one FAIL (warnings do not fail).
#
# Known problems you have decided to live with can be downgraded to warnings by namespace:
#   SKIP_NS='^(default)$' bash scripts/check-cluster.sh
# ok/wrn/bad below always return 0, so the `test && ok || bad` idiom used throughout is safe
# (SC2015 warns about the general case where the middle command can fail).
# shellcheck disable=SC2015
set -uo pipefail
export KUBECONFIG=${KUBECONFIG:-$HOME/.kube/config}
SKIP_NS=${SKIP_NS:-}

pass=0 fail=0 warn=0
ok()   { printf '  \033[32mOK\033[0m    %s\n' "$*"; pass=$((pass + 1)); }
wrn()  { printf '  \033[33mWARN\033[0m  %s\n' "$*"; warn=$((warn + 1)); }
# bad <message> [namespace]: a FAIL, unless the namespace matches SKIP_NS (then a WARN).
bad()  {
  if [ -n "$SKIP_NS" ] && [ -n "${2:-}" ] && [[ $2 =~ $SKIP_NS ]]; then wrn "$1 (ignored: namespace $2 in SKIP_NS)"; return; fi
  printf '  \033[31mFAIL\033[0m  %s\n' "$1"; fail=$((fail + 1))
}
sec()  { printf '\n== %s\n' "$*"; }

command -v kubectl >/dev/null || { echo "kubectl not found"; exit 2; }

sec "Node"
ready=$(kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}={.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}')
while IFS='=' read -r n s; do
  [ "$s" = True ] && ok "node $n Ready" || bad "node $n not Ready ($s)"
done <<<"$ready"
use=$(df --output=pcent /var/lib/rancher 2>/dev/null | tail -1 | tr -dc '0-9')
if [ -n "$use" ]; then
  if [ "$use" -ge 90 ]; then bad "disk /var/lib/rancher ${use}% used (PVC data lives here)"
  elif [ "$use" -ge 80 ]; then wrn "disk /var/lib/rancher ${use}% used"
  else ok "disk /var/lib/rancher ${use}% used"; fi
fi

sec "Fleet GitRepos and bundles"
while IFS=$'\t' read -r name rdy des; do
  [ -z "$name" ] && continue
  [ "${rdy:-0}" = "${des:-x}" ] && ok "gitrepo $name ($rdy/$des bundle deployments ready)" || bad "gitrepo $name not ready (${rdy:-0}/${des:-?})"
done < <(kubectl -n fleet-local get gitrepo -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.summary.ready}{"\t"}{.status.summary.desiredReady}{"\n"}{end}' 2>/dev/null)
while IFS=$'\t' read -r name rdy des; do
  [ -z "$name" ] && continue
  case $name in fleet-agent-*) continue;; esac
  [ "${rdy:-0}" = "${des:-x}" ] && ok "bundle $name" || bad "bundle $name not ready (${rdy:-0}/${des:-?}): $(kubectl -n fleet-local get bundle "$name" -o jsonpath='{.status.display.message}{.status.conditions[?(@.type=="Ready")].message}' 2>/dev/null | cut -c1-140)"
done < <(kubectl -n fleet-local get bundles -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.summary.ready}{"\t"}{.status.summary.desiredReady}{"\n"}{end}' 2>/dev/null)

sec "Workloads"
while IFS=$'\t' read -r ns name want have; do
  [ -z "$name" ] && continue
  [ "${have:-0}" = "${want:-1}" ] && ok "deploy $ns/$name ${have:-0}/${want}" || bad "deploy $ns/$name ${have:-0}/${want} available" "$ns"
done < <(kubectl get deploy -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.spec.replicas}{"\t"}{.status.availableReplicas}{"\n"}{end}')
badpods=$(kubectl get pods -A --no-headers 2>/dev/null | awk '$4!="Running" && $4!="Completed" {print $1"/"$2" "$4}')
[ -z "$badpods" ] && ok "no pods in a bad state" || while read -r l; do bad "pod $l" "${l%%/*}"; done <<<"$badpods"
restarts=$(kubectl get pods -A --no-headers 2>/dev/null | awk '{r=$5; sub(/ .*/,"",r); if (r+0>=10) print $1"/"$2" restarts="r}')
[ -n "$restarts" ] && while read -r l; do wrn "pod $l"; done <<<"$restarts"

sec "Storage"
while IFS=$'\t' read -r ns name phase; do
  [ -z "$name" ] && continue
  [ "$phase" = Bound ] && ok "pvc $ns/$name Bound" || bad "pvc $ns/$name $phase"
done < <(kubectl get pvc -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}')

sec "Certificates (cert-manager)"
while IFS=$'\t' read -r name rdy; do
  [ -z "$name" ] && continue
  [ "$rdy" = True ] && ok "clusterissuer $name Ready" || bad "clusterissuer $name not Ready"
done < <(kubectl get clusterissuer -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}' 2>/dev/null)
now=$(date +%s)
while IFS=$'\t' read -r ns name rdy exp; do
  [ -z "$name" ] && continue
  if [ "$rdy" != True ]; then bad "certificate $ns/$name not Ready" "$ns"; continue; fi
  days=$(( ($(date -d "$exp" +%s 2>/dev/null || echo "$now") - now) / 86400 ))
  [ "$days" -lt 10 ] && bad "certificate $ns/$name expires in ${days}d (renewal should have happened)" "$ns" || ok "certificate $ns/$name Ready, ${days}d left"
done < <(kubectl get certificate -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\t"}{.status.notAfter}{"\n"}{end}' 2>/dev/null)

sec "Sealed Secrets"
while IFS=$'\t' read -r ns name st; do
  [ -z "$name" ] && continue
  [ "$st" = True ] && ok "sealedsecret $ns/$name synced" || bad "sealedsecret $ns/$name not synced (wrong cert, name, or namespace?)"
done < <(kubectl get sealedsecret -A -o jsonpath='{range .items[*]}{.metadata.namespace}{"\t"}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Synced")].status}{"\n"}{end}' 2>/dev/null)

sec "Traefik"
args=$(kubectl -n kube-system get deploy traefik -o jsonpath='{..args}' 2>/dev/null)
echo "$args" | grep -q 'entryPoints.web.http.redirections.entryPoint.to' && ok "HTTP->HTTPS redirect configured" || bad "redirect args missing (chart values key changed? see docs/runbook.md)"

sec "Ingress endpoints (via this node)"
first=
while read -r ns hostlist; do
  for h in ${hostlist//,/ }; do
    [ "$h" = "<none>" ] && continue
    code=$(curl -sk -o /dev/null -m 10 -w '%{http_code}' --resolve "$h:443:127.0.0.1" "https://$h/" 2>/dev/null)
    case $code in 200|301|302|303|307|308|401|403) ok "https://$h -> $code";; *) bad "https://$h -> ${code:-no response}" "$ns";; esac
    if [ -z "$first" ] && { [ -z "$SKIP_NS" ] || ! [[ $ns =~ $SKIP_NS ]]; }; then first=$h; fi
  done
done < <(kubectl get ingress -A --no-headers -o custom-columns=NS:.metadata.namespace,HOSTS:.spec.rules[*].host 2>/dev/null | sort -u)
if [ -n "$first" ]; then
  code=$(curl -s -o /dev/null -m 10 -w '%{http_code}' --resolve "$first:80:127.0.0.1" "http://$first/" 2>/dev/null)
  [ "$code" = 308 ] || [ "$code" = 301 ] && ok "http://$first redirects ($code)" || bad "http://$first -> $code (expected a redirect)"
fi

printf '\n%d passed, %d warning(s), %d failed\n' "$pass" "$warn" "$fail"
[ "$fail" -eq 0 ]
