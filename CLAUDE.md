# CLAUDE.md

GitOps repo for a **single-node k3s cluster** managed through **Rancher** (Fleet). Everything here is Kubernetes YAML; there is no build step.

## Layout

- `infrastructure/<name>/` – cluster-wide config (e.g. cert-manager issuers).
- `fleet/gitrepo.yaml` – Fleet GitRepo bootstrap, applied by hand once; not inside Fleet's scanned paths.
- `apps/<name>/` – one directory per application (each is its own Fleet bundle).
- `docs/` – architecture, ingress, and per-app runbooks. Update docs when changing manifests.

## Conventions

- One namespace per app, named after the app; the manifest `namespace.yaml` lives in the app dir.
- One resource per file (`deployment.yaml`, `service.yaml`, `ingress.yaml`, `pvc.yaml`).
- Ingress uses the k3s-bundled **Traefik** (`ingressClassName: traefik`). Do not install a second ingress controller (e.g. ingress-nginx) without discussing it first; it would fight for ports 80/443.
- Routing is by subdomain: `<app>.k3s-node.home`. The router (UniFi) has a wildcard `*.k3s-node.home` pointing at the node; Rancher itself lives at `https://k3s-node.home`.
- TLS: cert-manager (installed by Rancher, not managed here) with a self-signed internal CA. Issuers live in `infrastructure/cert-manager-issuers/`; Ingresses use `cert-manager.io/cluster-issuer: k3s-node-ca-issuer`.
- Persistent data uses the `local-path` StorageClass (data lives on the node at `/var/lib/rancher/k3s/storage`).
- Pin image tags (never `latest`/`stable`); Renovate proposes bumps.
- Each app dir has a `fleet.yaml` (`defaultNamespace`, `dependsOn` for ordering). Bundle names are `k3s-cluster-<path with dashes>`.
- No secrets in git; see `docs/secrets.md`. Never commit kubeconfigs or keys.
- No backups are configured yet; take an HA backup before upgrades.
- CI runs kubeconform; new CRD-backed kinds are skipped by `-ignore-missing-schemas`.

## Workflow

- Changes reach the cluster by pushing to `main`; Fleet reconciles. Do not `kubectl apply` things that are managed here, or Fleet will revert/fight them.
- Validate before committing: `kubectl apply --dry-run=client -f <path>` (or `--dry-run=server` with a kubeconfig).
- Only commit/push when asked.

## Placeholders to fill in

- Timezone in `apps/home-assistant/deployment.yaml`.
