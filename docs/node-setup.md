# Node and network setup (not managed by Git)

Things that live on the node (`k3s-node5`, `192.168.0.246`) or the UniFi gateway. Fleet can't apply these, so record what you've done in the checklist at the bottom.

## 1. DHCP reservation (UniFi)

Everything depends on the node's address (the `*.k3s-node.home` wildcard points at it).
UniFi Network → Client Devices → `k3s-node5` → Settings → **Fixed IP Address** → `192.168.0.246`.

## 2. Automatic OS security updates

```sh
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

Optionally set a reboot window in `/etc/apt/apt.conf.d/50unattended-upgrades`:

```text
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
```

A reboot briefly takes everything down (single node); 04:00 keeps it out of the way. Pods come back on their own.

## 3. Disk health (SMART)

```sh
sudo apt install -y smartmontools
sudo smartctl -H /dev/sda        # or /dev/nvme0n1; use `lsblk` to find the disk
sudo systemctl enable --now smartd
```

Configure `smartd` to email or run a script on failure (`/etc/smartd.conf`), or just run `smartctl -H` monthly. SQLite databases (Home Assistant, Uptime Kuma) are the most sensitive to a failing disk or dirty power-off.

## 4. UPS and graceful shutdown

A dirty power-off is the most likely way to corrupt Home Assistant's database. If you have a UPS with USB, use NUT:

```sh
sudo apt install -y nut
# set MODE=standalone in /etc/nut/nut.conf, define the UPS in /etc/nut/ups.conf, then:
sudo systemctl enable --now nut-server nut-monitor
upsc <ups-name>
```

## 5. k3s snapshots of cluster state

This is cluster *state* (objects, secrets), not app data in PVCs. With the default SQLite datastore, copy `/var/lib/rancher/k3s/server/db/` while k3s is stopped, or use `k3s etcd-snapshot` if you switch to embedded etcd. Fleet makes this less critical because the manifests are in Git, but the **CA key** and any hand-made secrets are not (see [runbook.md](runbook.md#back-up-the-ca-key)).

## 6. k3s upgrades

Upgrade manually and deliberately (re-run the install script with `INSTALL_K3S_VERSION=...`), after checking the release notes. I did not install system-upgrade-controller: k3s bundles Traefik, and chart changes between versions already broke the redirect key once. After each upgrade verify Traefik's redirect args (see runbook).

## 7. Trusted certificates

Either trust the internal CA on each device ([ingress.md](ingress.md)) or move to a real domain: buy one, put its DNS on a provider cert-manager supports (e.g. Cloudflare), add a Let's Encrypt DNS-01 ClusterIssuer, and change the `host`s in the Ingresses.

## 8. Remote access

Prefer Tailscale (install on the node, advertise the LAN as a subnet route) over port-forwarding 443. Then `https://home-assistant.k3s-node.home` works away from home if the tailnet uses your gateway for DNS, or add Tailscale split DNS for `k3s-node.home`.

## Checklist

- [ ] DHCP reservation for 192.168.0.246
- [ ] unattended-upgrades enabled
- [ ] smartd running / SMART checked
- [ ] UPS + NUT (if available)
- [ ] CA key exported and stored offline
- [ ] CA trusted on PC and phone (or real domain)
- [ ] Tailscale (optional)
- [ ] Application backups (**not set up**, see [architecture.md](architecture.md#caveats))
