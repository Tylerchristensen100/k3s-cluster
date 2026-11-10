# Home Assistant

Manifests: [`apps/home-assistant/`](../apps/home-assistant). Namespace `home-assistant`, served at `https://home-assistant.k3s-node.home` (cert from the internal CA, see [ingress.md](ingress.md#tls-self-signed-internal-ca)).

## Before first deploy

1. Ensure the UniFi wildcard DNS record `*.k3s-node.home` points at the node ([ingress.md](ingress.md)).
2. Set `TZ` in `deployment.yaml`.
3. Push to `main`; Fleet applies it.

## Required: trust the reverse proxy

Home Assistant rejects proxied requests (400 Bad Request) until it trusts Traefik. After first start, edit `/config/configuration.yaml` on the volume:

```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 10.42.0.0/16   # k3s default pod CIDR
```

Edit it in place:

```sh
kubectl -n home-assistant exec -it deploy/home-assistant -- vi /config/configuration.yaml
kubectl -n home-assistant rollout restart deploy/home-assistant
```

Then open `https://home-assistant.k3s-node.home` and complete onboarding.

## Device discovery

Pod networking blocks mDNS/SSDP, so auto-discovery of LAN devices won't work by default. Options: add devices by IP, or uncomment `hostNetwork: true` and `dnsPolicy` in `deployment.yaml` (the pod then shares the node's network). USB dongles (Zigbee/Z-Wave) additionally need a `hostPath` device mount and `securityContext.privileged` or a device plugin; not configured yet.

## Network policy and resources

[`networkpolicy.yaml`](../apps/home-assistant/networkpolicy.yaml): only Traefik can reach port 8123; Home Assistant can reach DNS, the LAN and the internet, but not other pods or services in the cluster (`10.42.0.0/16`, `10.43.0.0/16`; adjust if you changed k3s CIDRs). Enabling `hostNetwork` bypasses the policy.

If an integration can't reach a device after deploy, check the policy first (`kubectl -n home-assistant describe networkpolicy`). Resources: requests 250m CPU / 512Mi, limits 2 CPU / 2Gi; raise if the UI is sluggish or the pod is OOM-killed.

## Operations

```sh
kubectl -n home-assistant get pods,pvc,ingress
kubectl -n home-assistant logs deploy/home-assistant -f
```

**Backups:** use HA's built-in backups (Settings → System → Backups) and copy them off-node; the config PVC lives on the node disk only.

**Upgrades:** change the image tag (currently pinned to `2026.11.1`), push, and Fleet rolls it out. Take a backup first. The `Recreate` strategy means a brief outage during rollout.
