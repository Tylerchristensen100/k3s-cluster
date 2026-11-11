---
description: Run the live read-only cluster health check over SSH and explain any failures
allowed-tools: Bash(ssh -o BatchMode=yes k3s-node@192.168.0.246 'bash -s' < scripts/check-cluster.sh)
argument-hint: [optional SKIP_NS regex, e.g. ^(default)$]
---

Run the health check against the real cluster. It is read-only.

1. Run exactly: `ssh -o BatchMode=yes k3s-node@192.168.0.246 'bash -s' < scripts/check-cluster.sh`
   If the user gave an argument ($ARGUMENTS), run it as `ssh -o BatchMode=yes k3s-node@192.168.0.246 "SKIP_NS='$ARGUMENTS' bash -s" < scripts/check-cluster.sh` instead (this needs the user to approve the command).
2. Strip ANSI colour codes when reading output. Summarize as: passed / warnings / failed counts, then each FAIL with its likely cause and fix, taken from `docs/runbook.md`.
3. Distinguish new problems from the known open issues listed in `CLAUDE.md` ("Known open issues"); say so explicitly for the known ones rather than re-diagnosing them.
4. Never run anything that changes the cluster. Cluster writes and `sudo` are the user's to run: give them copy-paste commands and say where each runs (PC PowerShell or the node).
