# AdGuard Home

Network-wide DNS resolver with caching and ad/tracker blocking. Admin UI: `https://adguard-home.k3s-node.home`. Manifests: [`apps/adguard-home`](../apps/adguard-home).

## How it is exposed

- Admin UI: Traefik ingress like every other app (container port 3000).
- DNS: `Service adguard-home-dns` (type `LoadBalancer`, k3s ServiceLB) publishes UDP/TCP 53 on the node IP (`192.168.0.246`). `externalTrafficPolicy: Local` keeps real client IPs in the query log.
- Port 53 on the node must be free. If `systemd-resolved` holds it, the svclb pod stays `Pending`; check with `ss -lunp | grep :53` on the node.

## First run

1. After Fleet deploys, open `https://adguard-home.k3s-node.home` (the setup wizard).
2. In the wizard set the **admin web interface port to 3000** (not 80) and the **DNS port to 53**. The probes, Service and NetworkPolicy assume 3000.
3. Create the admin user (store the password in a password manager).
4. Settings -> DNS settings: pick upstreams (e.g. `https://dns.quad9.net/dns-query`, `https://cloudflare-dns.com/dns-query`), enable parallel requests, and raise the cache size (e.g. 4 MB).
5. Filters -> DNS blocklists: the default list is fine to start.

## Point the network at it

In UniFi set the DHCP DNS server for the LAN to `192.168.0.246`, with a **secondary** such as `1.1.1.1` so the network keeps working if the node is down (some queries then bypass filtering). Test from a PC: `nslookup doubleclick.net 192.168.0.246` should return `0.0.0.0`.

Keep the UniFi wildcard `*.k3s-node.home` as is, or move it into AdGuard under Filters -> DNS rewrites (`*.k3s-node.home` -> `192.168.0.246`) and keep `k3s-node.home` for Rancher.

## Caveats

- DNS-level only: it blocks ad domains, not first-party ads (e.g. YouTube).
- Devices using hardcoded DNS or DNS-over-HTTPS bypass it.
- Single node, single replica: a node reboot briefly stops DNS.
- Data (config, query log, stats) is on `local-path` with **no backups**. Losing it only means redoing the setup.
- The image tag is pinned; bump it in `deployment.yaml` deliberately.
