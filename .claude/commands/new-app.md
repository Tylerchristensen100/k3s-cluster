---
description: Scaffold a new app under apps/ following the repo conventions
argument-hint: <name> <image:tag> <container-port>
allowed-tools: Bash(python scripts/lint.py), Bash(git status*)
---

Create `apps/$1` for image `$2` listening on port `$3`. If any of the three arguments is missing, ask for it.

1. Read `apps/uptime-kuma/` as the template and `CLAUDE.md` for the conventions. Create: `namespace.yaml`, `limits.yaml`, `pvc.yaml` (only if the app needs persistent data; ask), `deployment.yaml`, `service.yaml`, `ingress.yaml`, `networkpolicy.yaml`, `fleet.yaml`.
2. Rules (all enforced by `scripts/lint.py`): the namespace and `defaultNamespace` are `$1`; the image tag is pinned (never `latest`/`stable`); set requests (cpu, memory) and a memory limit plus readiness/liveness probes; the Ingress uses `ingressClassName: traefik`, host `$1.k3s-node.home`, `cert-manager.io/cluster-issuer: k3s-node-ca-issuer`, and a `tls` block; `fleet.yaml` has `dependsOn: github-infrastructure-cert-manager-issuers`.
3. Check the image's docs for host/Host-header validation, required environment variables, run-as user, and whether it writes to its root filesystem. Mention anything that could break probes (see the Homepage case in `docs/runbook.md`).
4. If the app needs secrets, do NOT create them. Tell the user which keys to seal (`scripts/seal.sh` or the web UI) and the exact Secret name and namespace to use.
5. Add the app to the Apps tables in `README.md` and `docs/README.md`, and to `apps/homepage/configmap.yaml`. Create `docs/$1.md` only if there is something non-obvious to record, and list it in `docs/README.md`.
6. Run `python scripts/lint.py` and fix every error. Do not commit or push. End by listing what the user must do (DNS is already a wildcard; secrets; first-run steps).
