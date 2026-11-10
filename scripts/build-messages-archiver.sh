#!/usr/bin/env bash
# Build messages-archiver on the k3s node and import it into k3s's containerd (no registry needed).
# Run ON THE NODE:   bash build-messages-archiver.sh        (needs podman, git, sudo)
# From your PC:      ssh -t k3s-node@192.168.0.246 'bash -s' < scripts/build-messages-archiver.sh
# Optional env: TAG=0.1.0 (default: appVersion from the chart), SRC=<checkout dir>.
set -euo pipefail

REPO_URL=${REPO_URL:-git@github.com:Tylerchristensen100/MessagesForWeb_Archiver.git}
SRC=${SRC:-$HOME/src/MessagesForWeb_Archiver}

mkdir -p "$(dirname "$SRC")"
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" pull --ff-only
else
  git clone "$REPO_URL" "$SRC"
fi

TAG=${TAG:-$(sed -n 's/^appVersion: *"\{0,1\}\([^"]*\)"\{0,1\} *$/\1/p' "$SRC/charts/messages-archiver/Chart.yaml")}
[ -n "$TAG" ] || { echo "could not determine image tag" >&2; exit 1; }

# docker.io/library/... so the pod's image name "messages-archiver:<tag>" resolves to it locally.
IMAGE="docker.io/library/messages-archiver:$TAG"
echo ">> building $IMAGE"
podman build -t "$IMAGE" "$SRC"

echo ">> importing into k3s containerd (sudo)"
podman save "$IMAGE" | sudo k3s ctr images import -

echo ">> restarting the deployment (no-op on first install)"
export KUBECONFIG=${KUBECONFIG:-$HOME/.kube/config}
kubectl -n messages-archiver rollout restart deploy/messages-archiver 2>/dev/null || echo "   (not deployed yet)"
echo ">> done: $IMAGE"
