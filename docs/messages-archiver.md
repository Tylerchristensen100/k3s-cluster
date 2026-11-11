# Messages Archiver

Private app from `Tylerchristensen100/MessagesForWeb_Archiver` (Go, Helm chart in `charts/messages-archiver`): archives your texts via Google Messages for web. Served at `https://messages-archiver.k3s-node.home` (HTTP Basic auth: any username, the `UI_PASSWORD`).

## How it fits together

| Piece | Where |
| --- | --- |
| Helm chart + `fleet.yaml` with cluster values | private repo, deployed by the `messages-archiver` GitRepo ([fleet/messages-archiver-gitrepo.yaml](../fleet/messages-archiver-gitrepo.yaml)), authenticated with the GitHub App secret `github-app-auth` |
| Namespace, quotas, **sealed secret** | this repo, `apps/messages-archiver/` (bundle `github-apps-messages-archiver`) |
| Container image | built **by hand on the node**, imported into k3s containerd (no registry) |

Bundle names: `github-apps-messages-archiver` (this repo) and `messages-archiver-charts-messages-archiver` (private repo). The chart bundle `dependsOn` the first, so the Secret exists before the pod starts. Overview: [architecture.md](architecture.md#the-private-app).

## One-time setup (in this order)

### 1. Install a build tool on the node

```sh
sudo apt install -y podman
```

### 2. Let the node clone the private repo (read-only deploy key)

Run these **on the node** (an interactive `ssh k3s-node@192.168.0.246` session or Terminus), not in your PC's PowerShell ([why](runbook.md#windows--powershell-gotchas)).

```sh
ssh-keygen -t ed25519 -f ~/.ssh/messages-archiver-deploy -N "" -C "k3s-node deploy key"
printf 'Host github.com\n  IdentityFile ~/.ssh/messages-archiver-deploy\n  IdentitiesOnly yes\n' > ~/.ssh/config
chmod 600 ~/.ssh/config
cat ~/.ssh/messages-archiver-deploy.pub
```

Add the printed **public** key to the private repo (Settings -> Deploy keys, leave write access unchecked), or from PowerShell:

```powershell
ssh k3s-node@192.168.0.246 'cat ~/.ssh/messages-archiver-deploy.pub' | gh repo deploy-key add - --repo Tylerchristensen100/MessagesForWeb_Archiver --title "k3s-node (read-only)"
```

Verify on the node: `ssh -T git@github.com` should say "successfully authenticated".

### 3. Seal the secrets

One Secret named `messages-archiver` in namespace `messages-archiver`, sealed as in [secrets.md](secrets.md) and saved as `apps/messages-archiver/secrets.sealed.yaml`. Keys: `UI_PASSWORD` (required, the app refuses to start without it), `drive_client_id`, `drive_client_secret`. The lowercase Drive key names are mapped in the chart values (step 4). Anything else can be added via `extraEnv` with a `secretKeyRef`.

### 4. Put the cluster values in the private repo

Copy [examples/messages-archiver-chart-fleet.yaml](examples/messages-archiver-chart-fleet.yaml) to `charts/messages-archiver/fleet.yaml` in the private repo and push to `main`. **Do this before creating the GitRepo (step 6)**, otherwise the chart renders with defaults and fails ("Set uiPassword").

### 5. Build and import the image

From PowerShell on your PC:

```powershell
Get-Content scripts\build-messages-archiver.sh -Raw | ssh -t k3s-node@192.168.0.246 'bash -s'
```

or copy the script to the node and run it there; sudo prompts for a password for the containerd import. It clones/pulls the private repo, builds `docker.io/library/messages-archiver:<appVersion>` with podman, imports it, and restarts the deployment. Verify: `sudo k3s ctr images ls | grep messages-archiver`.

### 6. Create the GitRepo

In Rancher: Continuous Delivery -> workspace **fleet-local** -> Git Repos -> Create -> Edit as YAML, paste [fleet/messages-archiver-gitrepo.yaml](../fleet/messages-archiver-gitrepo.yaml). Or `kubectl apply -f` it on the node. Then open the URL, pair the phone, and **Run now**.

The GitHub App secret (`github-app-auth` in `fleet-local`, fields `github_app_id`, `github_app_installation_id`, `github_app_private_key`) is created by hand and not stored in Git.

## Updating the app

Push code to the private repo, then re-run the build script on the node (step 5). It overwrites the same tag in containerd and restarts the pod. Chart changes deploy through Fleet when pushed. To change the version, bump `appVersion` in the chart.

## Operations and caveats

- `session.json` on the volume holds your Google account credentials and every message. Treat the volume as sensitive.
- **No backups are configured.** A disk failure loses the archive and the pairing; this is the main risk for this app.
- Egress is intentionally open (the app talks to Google); ingress is limited to Traefik and same-namespace pods by the chart's NetworkPolicy.
- `ImagePullBackOff`, `CreateContainerConfigError` and the red "namespace not owned" Fleet status are explained in the [runbook](runbook.md#workload-problems). The namespace one does not affect the running app.
- Health URL (no auth): `/healthz`.
