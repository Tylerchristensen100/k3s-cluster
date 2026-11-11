---
description: Run the repo checks and summarize what would be pushed (never pushes)
allowed-tools: Bash(python scripts/lint.py), Bash(shellcheck scripts/*.sh), Bash(git status*), Bash(git diff*), Bash(git log*)
---

Prepare the user to push safely. Do NOT commit or push.

1. Run `python scripts/lint.py` and `shellcheck scripts/*.sh` (skip ShellCheck with a note if it is not installed). Report errors exactly; explain each in one line using `docs/checks.md`.
2. Run `git status --short` and `git diff --stat`. Group the changes by area (apps, infrastructure, fleet, scripts, docs).
3. Flag anything risky in the diff: new or changed `*.sealed.yaml` (must be `kind: SealedSecret`), removed `Namespace` manifests (Helm deletes the namespace and its PVCs), changed `fleet.yaml` `dependsOn`/names, image or chart version changes, anything that could restart a stateful app.
4. State in one line which Fleet bundles the push will touch (`github-<path with dashes>`), and remind the user to run `scripts/check-cluster.sh` afterwards (see `/check-cluster`).
5. End with a ready/not-ready verdict and a suggested commit message. Ask before committing.
