# Messages Archiver

Private app from `Tylerchristensen100/MessagesForWeb_Archiver` (Go, Helm chart in `charts/messages-archiver`). Served at `https://messages-archiver.k3s-node.home`.

## How it fits together

| Piece | Where |
| --- | --- |
| Helm chart + `fleet.yaml` with cluster values | private repo, deployed by the `messages-archiver` GitRepo ([fleet/messages-archiver-gitrepo.yaml](../fleet/messages-archiver-gitrepo.yaml)), authenticated with the GitHub App secret `github-app-auth` |
| Namespace, quotas, **sealed secrets** | this repo, `apps/messages-archiver/` (bundle `github-apps-messages-archiver`) |
| Container image | built **by hand on the node**, imported into k3s containerd (no registry) |

The chart's bundle depends on the namespace/secrets bundle, so the Secret exists before the pod starts.

## One-time setup

### 1. Add the cluster values to the private repo

Copy [examples/messages-archiver-chart-fleet.yaml](examples/messages-archiver-chart-fleet.yaml) to `charts/messages-archiver/fleet.yaml` in the private repo and push to `main`.

### 2. Install a build tool on the node

Neither docker nor podman is installed. Podman needs no daemon:

```sh
sudo apt install -y podman
```

### 3. Let the node clone the private repo (read-only deploy key)

Run these **on the node** (an interactive `ssh k3s-node@192.168.0.246` session or Terminus), not in your PC's PowerShell. They are bash commands, and PowerShell can't parse them.

```sh
ssh-keygen -t ed25519 -f ~/.ssh/messages-archiver-deploy -N "" -C "k3s-node deploy key"
printf 'Host github.com\n  IdentityFile ~/.ssh/messages-archiver-deploy\n  IdentitiesOnly yes\n' >> ~/.ssh/config
chmod 600 ~/.ssh/config
cat ~/.ssh/messages-archiver-deploy.pub      # add to the private repo: Settings > Deploy keys (read-only)
ssh -T git@github.com                        # expect "successfully authenticated"
```

### 4. Seal the secrets

All of them go in **one** Secret named `messages-archiver` in namespace `messages-archiver`. The chart reads `UI_PASSWORD` and the Drive keys from it; other values can be added via `extraEnv` using `secretKeyRef`.

Use the Sealed Secrets web UI (`https://sealed-secrets-web.k3s-node.home`) or `kubeseal --cert certs/sealed-secrets-pub.pem`. Input, using real values (do not save this file, do not commit it):

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: messages-archiver
  namespace: messages-archiver
type: Opaque
stringData:
  UI_PASSWORD: <long password>
  DRIVE_CLIENT_ID: <...apps.googleusercontent.com>
  DRIVE_CLIENT_SECRET: <...>
  # add any other keys here
```

Save the sealed output as `apps/messages-archiver/sealed-secret.yaml` and commit it. The name and namespace are bound into the ciphertext, so it only decrypts as exactly this Secret.

### 5. Build the first image, then apply the GitRepo

```sh
ssh -t k3s-node@192.168.0.246 'bash -s' < scripts/build-messages-archiver.sh
kubectl apply -f fleet/messages-archiver-gitrepo.yaml     # or recreate it in Rancher
```

Bundle name: `messages-archiver-charts-messages-archiver`. Then open the UI, log in (any username, your `UI_PASSWORD`), pair the phone, and **Run now**.

## Updating the app

Push code to the private repo, then re-run [scripts/build-messages-archiver.sh](../scripts/build-messages-archiver.sh) on the node. It pulls, builds, imports the image and restarts the deployment. The tag is the chart's `appVersion`, so the same tag is overwritten in place. Chart changes deploy through Fleet when pushed.

## Caveats

- `session.json` on the volume holds your Google account credentials and all messages. Treat the volume as sensitive.
- **No backups are configured.** A disk failure loses the archive and the pairing; this is the main risk for this app.
- If the pod shows `ImagePullBackOff` / `ErrImageNeverPull`, the image isn't imported yet. Check with `sudo k3s ctr images ls | grep messages-archiver` (expect `docker.io/library/messages-archiver:<tag>`).
- Egress is intentionally open (the app talks to Google).
