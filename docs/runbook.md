# Runbook

Known problems and procedures, mostly learned the hard way during setup. `kubectl` on the node needs `export KUBECONFIG=~/.kube/config` in non-interactive shells.

## Back up the CA key

Every device that trusts `k3s-node-ca` depends on this key. If it's lost, re-trust a new CA everywhere.

```sh
kubectl -n cert-manager get secret k3s-node-ca-secret -o yaml > k3s-node-ca.secret.yaml
```

Store the file offline (password manager or encrypted drive). It is git-ignored (`*.secret.yaml`); never commit it.

**Restore on a rebuilt cluster:** `kubectl create namespace cert-manager` (if missing), `kubectl apply -f k3s-node-ca.secret.yaml`, *then* let Fleet sync the issuers bundle. cert-manager reuses the existing secret.

**Export the public cert** (safe to share) for trusting on devices:

```sh
kubectl -n cert-manager get secret k3s-node-ca-secret -o jsonpath='{.data.ca\.crt}' | base64 -d > k3s-node-ca.crt
```

## Fleet problems

| Symptom | Cause / fix |
| --- | --- |
| Bundle `...: invalid ownership metadata` | A resource exists from a different Helm release (e.g. after bundle layout changes). Delete that resource and let Fleet recreate it, then Force Update the GitRepo. |
| `WaitingForDependency` forever | The `dependsOn` bundle name is wrong. Names are `<GitRepo name>-<path with dashes>`; the GitRepo is `github`. |
| Everything lumped into one bundle named `github` | GitRepo `paths` is empty or a directory has no `fleet.yaml`. Set `paths: [infrastructure, apps]` and give each bundle dir a `fleet.yaml`. |
| A duplicate GitRepo keeps coming back | `fleet/gitrepo.yaml` was inside a scanned path. It must stay outside `paths`. |
| Private-repo chart fails with chart defaults (e.g. "Set uiPassword") | The `messages-archiver` GitRepo was created **before** `charts/messages-archiver/fleet.yaml` was pushed to the private repo. Push the file; Fleet re-polls every 60s, no need to recreate the GitRepo. |
| `namespace.v1 <name> is not owned by us` / Namespace "missing" | Two bundles deploy into the same namespace (the app bundle that owns `namespace.yaml` and a Helm-chart bundle). The workload keeps running; only Fleet's status is red. **Never fix it by deleting `namespace.yaml`**: Helm would delete the Namespace and with it the PVC (your data). If you ever must remove it, first add the annotation `helm.sh/resource-policy: keep` to it and let Fleet sync. Least destructive fix (untested): give the live namespace Helm ownership: `kubectl annotate ns <ns> meta.helm.sh/release-name=github-apps-<ns> meta.helm.sh/release-namespace=<ns> --overwrite && kubectl label ns <ns> app.kubernetes.io/managed-by=Helm --overwrite`, then Force Update. Verify with `scripts/check-cluster.sh`. |
| `Error getting keypair` / SealedSecret not synced | The sealed file was sealed with a different cluster's cert, or for a different name/namespace (strict scope). Re-export `certs/sealed-secrets-pub.pem` and re-seal. |
| GitRepo auth error for the private repo | Check secret `github-app-auth` in `fleet-local` has `github_app_id`, `github_app_installation_id`, `github_app_private_key` (`kubectl -n fleet-local describe secret github-app-auth` shows names and sizes only), that the App is installed on that repo, and that Fleet is >= 0.14. |

## Workload problems

| Symptom | Cause / fix |
| --- | --- |
| `ImagePullBackOff` for `messages-archiver:<tag>` | The image was built (podman) but not imported into k3s containerd, which needs sudo: `podman save docker.io/library/messages-archiver:<tag> \| sudo k3s ctr images import -`, verify with `sudo k3s ctr images ls \| grep messages-archiver`, then delete the pod. `scripts/build-messages-archiver.sh` does all of it. |
| Homepage crash-loops, log says `Host validation failed for: <pod ip>:3000` | Homepage rejects Host headers not in `HOMEPAGE_ALLOWED_HOSTS`, and kubelet probes use the pod IP. The probes in `apps/homepage/deployment.yaml` send `Host: homepage.k3s-node.home`; any new probe must too. |
| Pod `CreateContainerConfigError` | A referenced Secret/ConfigMap key doesn't exist. `kubectl describe pod` names it. For sealed secrets, check key names match what the chart expects (the messages-archiver values map `drive_client_id`/`drive_client_secret`). |
| A stray `rancher` Deployment in namespace `default` | Not from this repo: an old, broken Rancher install (missing `bootstrap-secret`, host `k3s-node.home.arpa`). The working Rancher is in `cattle-system`. Remove it if unwanted (`helm uninstall rancher -n default` if it is a Helm release), or silence it with `SKIP_NS='^(default)$'` in the health check. |

## Windows / PowerShell gotchas

You run commands from a Windows PC against a Linux node:

- **Bash heredocs (`<<'EOF'`) don't parse in PowerShell.** Run multi-line shell blocks on the node (interactive `ssh k3s-node@192.168.0.246` or Terminus), or use `printf`.
- **Windows PowerShell 5.1 strips inner double quotes** when passing arguments to `ssh`, so `"$(cat file)"` arrives unquoted and word-splits. Prefer `--from-file`, or run the command on the node.
- **`<` redirection isn't supported**; pipe instead: `Get-Content script.sh -Raw | ssh k3s-node@192.168.0.246 'bash -s'`.
- **Never paste placeholders** like `<APP_ID>`: the node's shell treats `<` as a redirect.
- Scripts must have LF line endings (`.gitattributes` enforces this).
| Resource shows `Modified` forever | The controller normalises a field. Use the normalised form, or add `diff.comparePatches` in that bundle's `fleet.yaml` (see the issuers bundle). |

## Traefik redirect not working

After any k3s upgrade, confirm:

```sh
kubectl -n kube-system get deploy traefik -o jsonpath='{..args}' | tr ',' '\n' | grep redirections
```

Expect three `entryPoints.web.http.redirections...` args. If missing, the chart's values key changed again; fix `infrastructure/traefik/helmchartconfig.yaml`.

## Home Assistant returns 400 / "not set-up for reverse proxies"

HTTP proxy trust lives in `/config/.storage/http` (Settings → System → Network), **not** `configuration.yaml`. Procedure in [home-assistant.md](home-assistant.md#required-trust-the-reverse-proxy).

## Certificate not issued

```sh
kubectl get clusterissuer                         # both READY True
kubectl -n <ns> get certificate,certificaterequest
kubectl -n <ns> describe certificate <name>
```

## Node won't boot / disk lost

1. Reinstall the OS and k3s, reinstall Rancher, recreate the `github` GitRepo (`fleet/gitrepo.yaml`).
2. Restore the CA secret (above) *before* the issuers bundle syncs.
3. Re-seal any secrets: the Sealed Secrets controller key is new, so previously sealed files won't decrypt unless you back up and restore its key (`kubectl -n kube-system get secret -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml`; store offline).
4. App data in PVCs is **gone unless you have backups** (none configured yet).

## Uptime Kuma first run

Open `https://uptime-kuma.k3s-node.home`, create the admin account, and add monitors, for example:
- HTTP(s) `https://home-assistant.k3s-node.home` (enable **Ignore TLS/SSL errors** unless the pod trusts the CA).
- HTTP(s) `https://k3s-node.home` (Rancher), `https://homepage.k3s-node.home`.
- A TCP/ping monitor on `192.168.0.246`.

Add a notification channel (ntfy, Telegram, email, or Home Assistant's mobile app via webhook) so failures reach you.

## Sealed Secrets

```sh
# install kubeseal on your PC, then:
kubectl create secret generic my-secret --dry-run=client -n <ns> --from-literal=key=value -o yaml \
  | kubeseal --controller-name sealed-secrets-controller --controller-namespace kube-system -o yaml > apps/<app>/my-secret.sealed.yaml
```

Commit only the `*.sealed.yaml` file (`.gitignore` allows it).
