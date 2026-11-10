# k3s-cluster

GitOps config for a single-node k3s cluster managed by Rancher. Pushing to `main` deploys via Fleet.

| Path | Contents |
| --- | --- |
| `apps/` | Applications (Home Assistant) |
| `infrastructure/` | Cluster-wide config: Traefik tweaks, cert-manager issuers |
| `fleet/` | Fleet `GitRepo` bootstrap (applied once by hand) |
| `docs/` | Architecture, ingress/TLS, Home Assistant, secrets |

Apps are served at `https://<app>.k3s-node.home` with certificates from an internal CA. Start with [docs/](docs/README.md).
