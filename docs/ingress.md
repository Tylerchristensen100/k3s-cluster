# Ingress (Traefik) and subdomains

k3s bundles Traefik, so no ingress controller needs installing. Verify it's running:

```sh
kubectl -n kube-system get pods -l app.kubernetes.io/name=traefik
kubectl get ingressclass          # expect: traefik
kubectl -n kube-system get svc traefik   # EXTERNAL-IP = node IP
```

## Routing by subdomain

Each app gets an `Ingress` with a `host` rule:

```yaml
spec:
  ingressClassName: traefik
  rules:
    - host: ha.example.com
```

## DNS

Point every subdomain at the node's IP. Easiest: one wildcard record.

| Scenario | Record |
| --- | --- |
| **This setup (LAN-only)** | UniFi local DNS: `*.k3s-node.home → <node LAN IP>` (wildcard; `k3s-node.home` itself keeps its own record for Rancher) |
| Public | `A *.example.com → <public IP>` (forward 80/443 on your router to the node) |
| No public exposure but remote access | Cloudflare Tunnel or Tailscale instead of port forwarding |

## TLS (self-signed internal CA)

`.home` is not a public TLD, so Let's Encrypt can't issue certs for it. Instead cert-manager runs a private CA, defined in [`infrastructure/cert-manager-issuers/issuers.yaml`](../infrastructure/cert-manager-issuers/issuers.yaml):

`selfsigned-bootstrap` → `k3s-node-ca` (10-year CA cert) → `k3s-node-ca-issuer` (signs app certs)

**Prerequisite:** cert-manager must already be installed (Rancher usually installs it). Check with:

```sh
kubectl get pods -n cert-manager
kubectl get crd certificates.cert-manager.io
```

If missing, install it first (e.g. `helm install cert-manager jetstack/cert-manager -n cert-manager --create-namespace --set crds.enabled=true`); do not install a second copy.

To get a cert for an app, add this to its Ingress:

```yaml
metadata:
  annotations:
    cert-manager.io/cluster-issuer: k3s-node-ca-issuer
spec:
  tls:
    - hosts: [<app>.k3s-node.home]
      secretName: <app>-tls
```

### Trusting the CA on your devices

Browsers warn until the CA is trusted. Export it once and install it as a trusted root on each device:

```sh
kubectl -n cert-manager get secret k3s-node-ca-secret -o jsonpath='{.data.ca\.crt}' | base64 -d > k3s-node-ca.crt
```

The Home Assistant mobile app also needs the CA installed on the phone's trust store.

Check issuance: `kubectl -n home-assistant get certificate` (READY should be `True`).

## Troubleshooting

- 404 from Traefik → Host header doesn't match any Ingress; check DNS and `host:`.
- 502/504 → Service has no ready endpoints: `kubectl -n <ns> get endpoints`.
- Port 80/443 already in use on the node → something else (another ingress, nginx on the host) is bound.
