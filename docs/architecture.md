# Architecture

```text
GitHub (this repo, main)
        │  Fleet GitRepo
        ▼
Rancher (Fleet) ──► k3s single node
                      ├─ Traefik (ingress, :80/:443)  ── routes by Host header
                      ├─ cert-manager (self-signed CA) ── TLS certs for Ingresses
                      ├─ local-path provisioner       ── PVCs on node disk
                      └─ apps: nginx test, home-assistant, ...
```

## Components

- **k3s** – single node, so no HA, and `ReadWriteOnce` local-path volumes are fine.
- **Rancher / Fleet** – watches this repo. Each directory containing manifests becomes a bundle; the root-level `nginx-deployment.yaml` is its own bundle.
- **Traefik** – ships with k3s, runs in `kube-system`, exposed through the built-in ServiceLB on the node's ports 80/443.

## Adding an app

1. Create `apps/<name>/` with namespace, workload, service, ingress (copy `apps/home-assistant`).
2. Pick a subdomain, add a DNS record (see [ingress.md](ingress.md)).
3. Push to `main` and watch the bundle in Rancher → Continuous Delivery.

## Fleet setup

[`fleet/gitrepo.yaml`](../fleet/gitrepo.yaml) defines the GitRepo (name `github`, matching the existing GitRepo in Rancher; paths `infrastructure` and `apps`). Bundle names derive from it (`github-apps-home-assistant`), and `apps/home-assistant/fleet.yaml` uses `dependsOn` so cert issuers sync first. If the GitRepo is renamed, update the `dependsOn` name.

CI (`.github/workflows/validate.yaml`) runs kubeconform on every push/PR. Renovate (`renovate.json`) proposes image-tag bumps once the Renovate GitHub app is installed on the repo.

## Caveats

- **No backups yet.** Single node: a node failure means downtime, and local-path data (including the Home Assistant config) exists only on that disk. Until a backup strategy exists, use Home Assistant's built-in backups and copy them off the node by hand. Future options: Longhorn snapshots/backups, or a CronJob copying `/var/lib/rancher/k3s/storage` to a NAS.
- The HTTP→HTTPS redirect (`infrastructure/traefik/`) assumes Traefik v3 (recent k3s). Check `kubectl -n kube-system get deploy traefik -o jsonpath='{.spec.template.spec.containers[0].image}'`.
