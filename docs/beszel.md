# Beszel

Lightweight server monitoring (CPU, RAM, disk, network, containers). UI: `https://beszel.k3s-node.home`. Manifests: [`apps/beszel`](../apps/beszel). Data is on `local-path` with **no backups**.

This bundle deploys the **hub** (web UI). The hub gets metrics from an **agent**, which needs a public key that the hub only generates after the first login, so the agent is a second step.

## 1. Create the admin user

Open the URL and create the first user (it becomes the admin).

## 2. Add the node and its agent

1. In the UI choose **Add System**, name it `k3s-node`, host `192.168.0.246`, port `45876`. Copy the **public key** shown.
2. Add `apps/beszel/agent.yaml` (a DaemonSet running `henrygd/beszel-agent` with `hostNetwork: true`, port `45876`, `KEY` set to that public key, `/proc`-style host metrics). Ask Claude to generate it once you have the key; the public key is not secret.
3. After the agent is running the system turns green in the hub.

`hostNetwork` agents bypass NetworkPolicy; the agent only accepts connections authenticated with the hub's key. The hub's NetworkPolicy already allows egress to the LAN.
