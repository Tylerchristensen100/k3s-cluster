# Docs

| Doc | Purpose |
| --- | --- |
| [architecture.md](architecture.md) | How the cluster, Rancher/Fleet, and this repo fit together; adding an app |
| [adguard-home.md](adguard-home.md) | AdGuard Home: first-run setup, router DNS, rewrites |
| [ingress.md](ingress.md) | Subdomain routing with Traefik, DNS, and TLS (internal CA) |
| [secrets.md](secrets.md) | Sealed Secrets: how to seal, what exists, what is outside Git |
| [checks.md](checks.md) | What is validated, in CI and live, and how to run it |
| [runbook.md](runbook.md) | Troubleshooting, CA key backup, PowerShell gotchas |
| [bootstrap.md](bootstrap.md) | Rebuilding the cluster from scratch, in order |
| [node-setup.md](node-setup.md) | Node/network tasks outside Git (DHCP, updates, SMART, UPS, access) |
| [home-assistant.md](home-assistant.md) | Deploying and operating Home Assistant |
| [messages-archiver.md](messages-archiver.md) | Private app: build on node, sealed secrets, Fleet + GitHub App |

## Apps

| App | URL | Path |
| --- | --- | --- |
| Rancher | `https://k3s-node.home` | (not in this repo) |
| Home Assistant | `https://home-assistant.k3s-node.home` | `apps/home-assistant` |
| Homepage (dashboard) | `https://homepage.k3s-node.home` | `apps/homepage` |
| Uptime Kuma (monitoring) | `https://uptime-kuma.k3s-node.home` | `apps/uptime-kuma` |
| AdGuard Home (DNS + ad blocking) | `https://adguard-home.k3s-node.home` | `apps/adguard-home` |
| Messages Archiver | `https://messages-archiver.k3s-node.home` | `apps/messages-archiver` + private repo chart |
| Sealed Secrets web UI (seal-only) | `https://sealed-secrets-web.k3s-node.home` | `apps/sealed-secrets-web` |

Infrastructure bundles (`infrastructure/`): `cert-manager-issuers`, `traefik`, `sealed-secrets`.
