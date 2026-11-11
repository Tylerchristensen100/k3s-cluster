# CLAUDE.md

GitOps repo for a **single-node k3s cluster** managed through **Rancher** (Fleet). Everything here is Kubernetes YAML and shell/Python helpers; there is no build step. Human-facing overview: `README.md` and `docs/`.

## Layout

- `apps/<name>/` – one directory per application (each is its own Fleet bundle).
- `infrastructure/<name>/` – cluster-wide config (cert-manager issuers, Traefik tweaks, Sealed Secrets controller).
- `fleet/*.yaml` – Fleet `GitRepo` definitions, applied by hand; **must stay outside** the GitRepo's scanned paths.
- `scripts/` – `lint.py` (static checks), `check-cluster.sh` (live read-only health), `seal.sh`, `build-messages-archiver.sh`.
- `certs/sealed-secrets-pub.pem` – public sealing cert (safe to commit). No other keys/certs.
- `docs/` – architecture, ingress/TLS, secrets, checks, runbook, bootstrap, per-app docs. `docs/examples/` holds copies of files that live in other repos.
- `.claude/` – shared Claude Code config: `settings.json` (permissions + secrets-guard hook), `hooks/block-secrets.py`, slash commands `/pre-push`, `/check-cluster`, `/new-app`. Personal overrides go in the git-ignored `settings.local.json`.

## Conventions (enforced by `python scripts/lint.py`)

- One namespace per app, named after the app directory; `defaultNamespace` in `fleet.yaml` matches it.
- Every bundle directory has a `fleet.yaml`. The GitRepo is named `github` with `paths: [infrastructure, apps]`, so bundle names are `github-<path with dashes>`; `dependsOn` uses those names.
- Ingress: `ingressClassName: traefik`, host `<app>.k3s-node.home`, TLS via `cert-manager.io/cluster-issuer: k3s-node-ca-issuer`. Do not add a second ingress controller (Traefik owns ports 80/443).
- Pin image tags and Helm chart versions (never `latest`/`stable`); set requests/limits and probes; give every app a NetworkPolicy, and a LimitRange/ResourceQuota.
- New apps: copy `apps/uptime-kuma`, then add to `apps/homepage/configmap.yaml` and the Apps table in `docs/README.md` and `README.md`.
- Persistent data uses `local-path` (on the node at `/var/lib/rancher/k3s/storage`). **No backups are configured**; say so rather than implying data is safe.
- **Secrets:** never commit a plaintext `Secret`; use Sealed Secrets (`docs/secrets.md`). Never commit kubeconfigs, `*.pem`/`*.key`, or the GitHub App key. Don't print secret values; `kubectl describe secret` shows names only.
- Write fields in the form controllers normalise to (e.g. cert-manager `87600h0m0s`) to avoid Fleet drift.
- **Never remove a `Namespace` manifest from a bundle**: Helm would delete the namespace and its PVCs. Use `helm.sh/resource-policy: keep` first.
- Update the docs in the same change as the manifests.

## Environment

- Claude has no kubectl access to the real cluster from this machine (the local context is Rancher Desktop). Read-only checks go over SSH: `ssh k3s-node@192.168.0.246`, with `export KUBECONFIG=~/.kube/config` in non-interactive shells. Cluster writes, `sudo`, and writes to the private repo are done by the user; give them copy-paste commands.
- The user is on Windows PowerShell 5.1 and the node is Linux: heredocs, inner double quotes and `<` redirection break (see `docs/runbook.md`). Tell the user where each command runs (PC or node).
- Fleet reconciles from `main`. Do not `kubectl apply` things managed here.
- Only commit/push when asked.

## Checks

- Before committing: `python scripts/lint.py` (needs PyYAML). CI also runs ShellCheck, kubeconform and a plaintext-Secret guard.
- After a deploy: `ssh k3s-node@192.168.0.246 'bash -s' < scripts/check-cluster.sh` (`SKIP_NS` downgrades accepted problems to warnings).
- A `PreToolUse` hook (`.claude/hooks/block-secrets.py`) blocks Write/Edit of a plaintext `kind: Secret` under `apps/`, `infrastructure/`, `fleet/`, and of any `*.pem`/`*.key`/kubeconfig file. If it blocks you, seal the secret instead; do not work around it.
- Details: `docs/checks.md`. Known gotchas (Fleet naming/ownership, Traefik chart keys, HA `.storage/http`, node-built images): `docs/runbook.md`.

## Known open issues

- `github-apps-messages-archiver` is red in Fleet ("namespace not owned by us"); the app runs. See runbook.
- A stray broken `rancher` Deployment in namespace `default` (not from this repo).
- Timezone in `apps/home-assistant/deployment.yaml` is a guess.
