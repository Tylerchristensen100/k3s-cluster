# k3s-cluster

GitOps config for a single-node k3s cluster (`k3s-node`, Rancher + Fleet). Pushing to `main` deploys.

| Path | Contents |
| --- | --- |
| `apps/` | One directory (= one Fleet bundle) per application |
| `infrastructure/` | Cluster-wide config: Traefik HTTPS redirect, cert-manager CA issuers, Sealed Secrets controller |
| `fleet/` | Fleet `GitRepo` definitions, applied once by hand (never inside a scanned path) |
| `scripts/` | `lint.py` (static checks), `check-cluster.sh` (live health), `seal.sh`, `build-messages-archiver.sh` |
| `certs/` | Sealed Secrets **public** certificate (encrypt-only) |
| `docs/` | Everything else: start at [docs/README.md](docs/README.md) |

## What runs

| App | URL |
| --- | --- |
| Rancher (not in this repo) | `https://k3s-node.home` |
| Home Assistant | `https://home-assistant.k3s-node.home` |
| Homepage (dashboard) | `https://homepage.k3s-node.home` |
| Uptime Kuma (monitoring) | `https://uptime-kuma.k3s-node.home` |
| Sealed Secrets web UI | `https://sealed-secrets-web.k3s-node.home` |
| Messages Archiver (private app) | `https://messages-archiver.k3s-node.home` |

Everything is served over HTTPS from an internal CA (trust it on your devices: [docs/ingress.md](docs/ingress.md)). DNS is a UniFi wildcard `*.k3s-node.home`.

## Everyday tasks

```sh
python scripts/lint.py                        # before every push (also runs in CI)
Get-Content scripts\check-cluster.sh -Raw | ssh k3s-node@192.168.0.246 'bash -s'   # live health, from PowerShell
scripts/seal.sh <ns> <name> apps/<app>/<name>.sealed.yaml KEY=VALUE   # seal a secret (or use the web UI)
```

| I want to... | Read |
| --- | --- |
| Add an app | [docs/architecture.md](docs/architecture.md#adding-an-app) |
| Add a secret | [docs/secrets.md](docs/secrets.md) |
| Know what is checked and how | [docs/checks.md](docs/checks.md) |
| Fix something broken | [docs/runbook.md](docs/runbook.md) |
| Rebuild the cluster | [docs/bootstrap.md](docs/bootstrap.md) |
| Do node/network tasks (DHCP, updates, UPS) | [docs/node-setup.md](docs/node-setup.md) |

## Known gaps

- **No backups.** App data lives on one disk. This is the biggest risk (see [docs/architecture.md](docs/architecture.md#caveats)).
- A broken, unrelated `rancher` deployment sits in the `default` namespace (see [docs/runbook.md](docs/runbook.md#workload-problems)).
- Fleet shows `github-apps-messages-archiver` red (namespace ownership); the app itself runs (see [docs/runbook.md](docs/runbook.md#fleet-problems)).
