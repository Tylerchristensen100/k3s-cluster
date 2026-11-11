# Rebuilding from scratch

Order matters; several steps failed in the original setup when done out of order. App data in PVCs is **not recoverable** unless you have backups (none are configured yet, see [architecture.md](architecture.md#caveats)).

## Things you must have saved before a disaster

| Item | Why | Where to keep it |
| --- | --- | --- |
| CA secret (`cert-manager/k3s-node-ca-secret`) | Every device trusts this CA | Offline, see [runbook.md](runbook.md#back-up-the-ca-key) |
| Sealed Secrets controller key | Without it every `*.sealed.yaml` is undecryptable and must be re-sealed | Offline: `kubectl -n kube-system get secret -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml` |
| GitHub App private key | Fleet access to the private repo | Password manager (or generate a new one) |
| Google OAuth client for Drive | Part of the sealed secret | Google Cloud Console |
| Home Assistant / archiver backups | App data | Nowhere yet |

## Steps

1. **OS and network.** Install the OS, give the node a DHCP reservation (`192.168.0.246`), and apply the items in [node-setup.md](node-setup.md).
2. **k3s.** Install k3s with the defaults, so Traefik, ServiceLB and `local-path` stay enabled.
3. **Rancher.** Install Rancher (this creates `cert-manager` and Fleet). It is not managed by this repo and lives at `https://k3s-node.home`.
4. **DNS.** In UniFi create `*.k3s-node.home` -> `192.168.0.246` (see [ingress.md](ingress.md)).
5. **Restore secrets that Git can't hold.**
   - CA: `kubectl create namespace cert-manager` then `kubectl apply -f k3s-node-ca.secret.yaml` **before** the issuers bundle syncs ([runbook](runbook.md#back-up-the-ca-key)).
   - Sealed Secrets key: apply the saved key secret into `kube-system` after the controller installs, then restart the controller. If you can't, re-export `certs/sealed-secrets-pub.pem` and re-seal every `*.sealed.yaml`.
   - `github-app-auth` in `fleet-local` ([messages-archiver.md](messages-archiver.md)).
6. **Fleet.** Create the `github` GitRepo from [`fleet/gitrepo.yaml`](../fleet/gitrepo.yaml) in workspace `fleet-local` (name and `paths` matter). Wait until `github-infrastructure-*` are Ready, then the apps.
7. **Home Assistant.** After first start, set proxy trust in `.storage/http` ([home-assistant.md](home-assistant.md#required-trust-the-reverse-proxy)).
8. **Messages Archiver.** Install podman, add the deploy key, run `scripts/build-messages-archiver.sh`, push the cluster `fleet.yaml` to the private repo, then create the `messages-archiver` GitRepo ([messages-archiver.md](messages-archiver.md)).
9. **Trust the CA** on your devices ([ingress.md](ingress.md)).
10. **Verify.** `scripts/check-cluster.sh` should end with 0 failed ([checks.md](checks.md)).
