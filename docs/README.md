# Docs

| Doc | Purpose |
| --- | --- |
| [architecture.md](architecture.md) | How the cluster, Rancher/Fleet, and this repo fit together |
| [ingress.md](ingress.md) | Subdomain routing with Traefik, DNS, and TLS |
| [home-assistant.md](home-assistant.md) | Deploying and operating Home Assistant |
| [secrets.md](secrets.md) | Secret-handling options and policy |
| [node-setup.md](node-setup.md) | Node/network tasks outside Git (DHCP, updates, SMART, UPS, access) |
| [runbook.md](runbook.md) | Troubleshooting, CA key backup, first-run steps |
| [messages-archiver.md](messages-archiver.md) | Private app: build on node, sealed secrets, Fleet + GitHub App |

## Apps

| App | URL | Path |
| --- | --- | --- |
| Rancher | `https://k3s-node.home` | (not in this repo) |
| Home Assistant | `https://home-assistant.k3s-node.home` | `apps/home-assistant` |
| Homepage (dashboard) | `https://homepage.k3s-node.home` | `apps/homepage` |
| Uptime Kuma (monitoring) | `https://uptime-kuma.k3s-node.home` | `apps/uptime-kuma` |
| Messages Archiver | `https://messages-archiver.k3s-node.home` | `apps/messages-archiver` + private repo chart |
| Sealed Secrets web UI (seal-only) | `https://sealed-secrets-web.k3s-node.home` | `apps/sealed-secrets-web` |
