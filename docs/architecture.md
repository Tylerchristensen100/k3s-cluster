# Architecture

```text
GitHub: k3s-cluster (public)            GitHub: MessagesForWeb_Archiver (private)
        │ Fleet GitRepo "github"                │ Fleet GitRepo "messages-archiver"
        │ paths: infrastructure, apps           │ path: charts/messages-archiver
        │                                       │ auth: GitHub App secret (github-app-auth)
        ▼                                       ▼
Rancher (Fleet) ───────────────► k3s single node (k3s-node5, 192.168.0.246)
                      ├─ Traefik (ingress, :80/:443)  ── routes by Host header, HTTP->HTTPS redirect
                      ├─ cert-manager (internal CA)   ── TLS certs for every Ingress
                      ├─ local-path provisioner       ── PVCs on node disk
                      ├─ sealed-secrets controller    ── decrypts *.sealed.yaml from Git
                      └─ apps: home-assistant, homepage, uptime-kuma, sealed-secrets-web, messages-archiver
```

## Components

- **k3s** – single node, so no HA, and `ReadWriteOnce` local-path volumes are fine.
- **Rancher / Fleet** – watches this repo. Each directory under `apps/` and `infrastructure/` with a `fleet.yaml` becomes a bundle named `github-<path with dashes>`.
- **Traefik** – ships with k3s, runs in `kube-system`, exposed through the built-in ServiceLB on the node's ports 80/443. `infrastructure/traefik` adds the HTTP-to-HTTPS redirect.
- **cert-manager** – installed by Rancher. `infrastructure/cert-manager-issuers` creates a self-signed CA and the `k3s-node-ca-issuer` ClusterIssuer.
- **Sealed Secrets** – `infrastructure/sealed-secrets` (controller) and `apps/sealed-secrets-web` (seal-only web UI). See [secrets.md](secrets.md).

## Bundle ordering

`dependsOn` in each `fleet.yaml` (names are `github-<path>`):

```text
cert-manager-issuers ──► home-assistant, homepage, uptime-kuma, sealed-secrets-web ──┐
sealed-secrets ─────────► sealed-secrets-web                                         │
apps/messages-archiver (namespace + sealed secret) ──► [private repo chart bundle]   ┘
```

`scripts/lint.py` verifies every `dependsOn` name exists.

## The private app

Messages Archiver is deliberately split across two repos and two GitRepos:

| What | Where | Why |
| --- | --- | --- |
| Helm chart + `fleet.yaml` (non-secret cluster values) | private repo | The chart belongs with the code |
| Namespace, quotas, **sealed secrets** | `apps/messages-archiver/` here | Instance-specific values stay with the cluster config |
| Container image | built by hand on the node, imported into k3s containerd | No registry; update with `scripts/build-messages-archiver.sh` |

Details: [messages-archiver.md](messages-archiver.md).

## Adding an app

1. Copy `apps/uptime-kuma/` (namespace, quotas, workload, service, NetworkPolicy, TLS ingress, `fleet.yaml` with `dependsOn` the issuers). The directory name, namespace, and `defaultNamespace` must match.
2. Pin the image tag; set requests/limits and probes.
3. If it needs a secret, seal it ([secrets.md](secrets.md)); never commit a plain `Secret`.
4. Host is `<app>.k3s-node.home`; DNS is already a wildcard.
5. Add it to `apps/homepage/configmap.yaml` and the Apps table in [README.md](README.md).
6. `python scripts/lint.py`, push, then run `scripts/check-cluster.sh` ([checks.md](checks.md)).

## Fleet setup

[`fleet/gitrepo.yaml`](../fleet/gitrepo.yaml) records the GitRepo (name `github`; paths `infrastructure` and `apps`). **The paths matter**: with none, Fleet scans the whole repo, lumps directories without a `fleet.yaml` into one root bundle named `github`, and would redeploy `fleet/gitrepo.yaml` itself. The name matters too, because bundle names and `dependsOn` derive from it. [`fleet/messages-archiver-gitrepo.yaml`](../fleet/messages-archiver-gitrepo.yaml) is the second GitRepo. Both are applied by hand (or recreated in Rancher) and are not scanned.

CI (`.github/workflows/validate.yaml`) runs `scripts/lint.py`, ShellCheck and kubeconform on every push and PR. Renovate (`renovate.json`) proposes image and chart bumps once its GitHub app is installed on the repo.

## Caveats

- **No backups yet.** Single node: a node failure means downtime, and local-path data (Home Assistant config, Uptime Kuma data, the message archive and its Google session) exists only on that disk. Use Home Assistant's built-in backups and copy them off the node by hand. Future options: Longhorn snapshots/backups, or a CronJob copying `/var/lib/rancher/k3s/storage` to a NAS or object storage.
- The HTTP-to-HTTPS redirect uses the Traefik chart key `ports.web.http.redirections`. It broke once when the key changed; `scripts/check-cluster.sh` verifies it after upgrades.
- The Sealed Secrets controller key and the CA key exist only in the cluster. Back them up ([bootstrap.md](bootstrap.md)).
