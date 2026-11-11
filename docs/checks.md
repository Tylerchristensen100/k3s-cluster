# Checks

Three layers, from cheapest to most thorough. Run the first two before you push; run the third after a deploy or whenever something feels off.

| Layer | Command | Where | What it catches |
| --- | --- | --- | --- |
| Repo conventions | `python scripts/lint.py` | your PC, CI | Bad manifests before they reach the cluster |
| Shell scripts | `shellcheck scripts/*.sh` | CI (optionally your PC) | Bugs in the helper scripts |
| Schema | kubeconform | CI | Invalid built-in Kubernetes kinds |
| Plaintext secrets | grep guard + lint | CI, lint | A `kind: Secret` committed to `apps/`, `infrastructure/`, `fleet/` |
| Before the file exists | Claude Code hook `.claude/hooks/block-secrets.py` | your editor session | Plaintext Secrets and key files being written at all (see [below](#claude-code-guardrails)) |
| Live health | `scripts/check-cluster.sh` | the node (or via ssh) | The cluster not matching the repo |
| Uptime | Uptime Kuma monitors | in-cluster | Outages between manual checks |

## `scripts/lint.py` (static)

Needs Python and PyYAML (`pip install pyyaml`). Exit code 1 on any error; warnings are advisory.

| Rule | Why |
| --- | --- |
| Every dir under `apps/` and `infrastructure/` has a `fleet.yaml` | Otherwise Fleet lumps it into a root bundle (see [runbook](runbook.md#fleet-problems)) |
| Apps set `defaultNamespace`; namespaced resources match it; `Namespace` is named after the directory | One namespace per app |
| Helm charts in `fleet.yaml` pin `helm.version` | Reproducible deploys |
| Container images have a tag and it isn't `latest`/`stable`/`main`/... | Pinned, Renovate-friendly |
| Containers set `requests.cpu`, `requests.memory`, `limits.memory`; probes missing = warning | Keeps one app from starving the single node |
| Apps with a Deployment/StatefulSet have a NetworkPolicy (LimitRange/ResourceQuota = warning) | Default-deny posture for what we run |
| Ingress: `ingressClassName: traefik`, host ends `.k3s-node.home`, covered by `tls`, annotated with the CA issuer | Every app is HTTPS from the internal CA |
| No plaintext `Secret`; `*.sealed.yaml` contains only `SealedSecret` with `encryptedData` | The `!*.sealed.yaml` gitignore exception is not a safety net |
| `dependsOn` names resolve to real bundles (`github-<path with dashes>`) | Prevents the "WaitingForDependency forever" trap |
| `fleet/gitrepo.yaml` is named `github` with `paths` exactly `apps`, `infrastructure` | Wrong paths recreate the root-bundle mess |
| No `*.pem`, `*.key`, `*.crt`, kubeconfig files in the tree (except the public sealed-secrets cert) | Credentials never reach Git |
| Markdown relative links and `#anchors` resolve; every `docs/*.md` is in the index; every app is in the Apps table | Docs don't rot silently |

When you add a rule, add a deliberately broken case to your test and confirm it fails. That is how this linter was validated.

## `scripts/check-cluster.sh` (live, read-only)

Changes nothing. Prints OK / WARN / FAIL per check and exits non-zero on any FAIL.

```sh
# from PowerShell on your PC
Get-Content scripts\check-cluster.sh -Raw | ssh k3s-node@192.168.0.246 'bash -s'
# on the node
bash scripts/check-cluster.sh
# downgrade known, accepted problems in a namespace to warnings
SKIP_NS='^(default)$' bash scripts/check-cluster.sh
```

It checks: node Ready and disk usage under `/var/lib/rancher`; every Fleet GitRepo and bundle Ready; all Deployments available and no pods in a bad state (plus restart-count warnings); PVCs Bound; ClusterIssuers and Certificates Ready with days to expiry; SealedSecrets decrypted (Synced); the Traefik HTTP-to-HTTPS redirect args; every Ingress host answers over HTTPS (200/3xx/401/403 are fine) and HTTP redirects.

Adding an app adds its checks automatically; nothing to maintain.

## Uptime Kuma monitors (set up in the UI)

Not code, so record them here. Enable **Ignore TLS/SSL errors** on HTTPS monitors unless the Kuma pod trusts the internal CA, and add one notification channel.

| Monitor | Type | Target | Accept |
| --- | --- | --- | --- |
| Rancher | HTTP(s) | `https://k3s-node.home` | 200 |
| Home Assistant | HTTP(s) | `https://home-assistant.k3s-node.home` | 200 |
| Homepage | HTTP(s) | `https://homepage.k3s-node.home` | 200 |
| Messages Archiver | HTTP(s) | `https://messages-archiver.k3s-node.home/healthz` | 200 |
| Sealed Secrets web | HTTP(s) | `https://sealed-secrets-web.k3s-node.home` | 200 |
| Node | Ping | `192.168.0.246` | up |
| CA certificate expiry | HTTP(s) with expiry notification | any of the above | alert at 14 days |

Uptime Kuma can't see inside the cluster (volume fill, bundle drift, crash loops); that is what `check-cluster.sh` is for.

## Claude Code guardrails

Committed in `.claude/` so they apply to anyone using Claude Code on this repo:

| Piece | What it does |
| --- | --- |
| `hooks/block-secrets.py` (PreToolUse on Write/Edit) | Denies writing a plaintext `kind: Secret` into `apps/`, `infrastructure/` or `fleet/` YAML, and any `*.pem`, `*.key`, `*.age`, kubeconfig or `k3s.yaml` file (the public `certs/sealed-secrets-pub.pem` is allowed). CI catches these after a push; this stops them before the file exists. |
| `settings.json` permissions | Auto-allows the safe local commands (`lint.py`, ShellCheck, read-only git). Denies reading key files, `~/.ssh`, `~/.kube`, and force pushes. SSH to the node is deliberately **not** auto-allowed. |
| `/pre-push` | Runs lint + ShellCheck, summarizes the diff, flags risky changes. Never pushes. |
| `/check-cluster` | Runs the live health check over SSH and explains failures from the runbook. |
| `/new-app <name> <image:tag> <port>` | Scaffolds `apps/<name>` from the Uptime Kuma template and runs the linter. |

Hooks load when Claude Code starts. After pulling a change to `.claude/settings.json`, open `/hooks` once or restart the session.

To test the hook after editing it, pipe a payload into it (generate the JSON with `json.dumps`; hand-typed Windows paths break on backslash escaping):

```sh
python -c "import json;print(json.dumps({'tool_name':'Write','tool_input':{'file_path':'apps/x/s.yaml','content':'kind: Secret'}}))" | python .claude/hooks/block-secrets.py
```

It prints a `deny` decision to block and prints nothing to allow.

## After every deploy

1. `python scripts/lint.py` before pushing.
2. Watch Rancher → Continuous Delivery, or run `check-cluster.sh` a minute after the push.
3. For anything new, open its URL once.

## Not covered yet

- **Backups and restore tests.** None are configured, so there is nothing to verify. This is the largest gap; see [architecture.md](architecture.md#caveats).
- Disk-fill and database-health alerts (needs a metrics stack or a CronJob).
- Helm-chart rendering in CI (`helm template`) for the private chart.
