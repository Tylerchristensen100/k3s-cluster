#!/usr/bin/env python3
"""PreToolUse hook (Write|Edit): stop secrets before they reach the repo.

Blocks:
  1. A plaintext Kubernetes `kind: Secret` written into apps/, infrastructure/ or fleet/ YAML
     (only SealedSecrets may be committed; see docs/secrets.md).
  2. Writing private-key / credential-looking files (*.pem, *.key, kubeconfig, k3s.yaml, *.age)
     anywhere in the repo, except the public sealing cert certs/sealed-secrets-pub.pem.

Reads the hook JSON on stdin. Prints a PreToolUse "deny" decision to block; prints nothing to allow.
"""
import json
import re
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # never break the session on malformed input

ti = data.get("tool_input") or {}
path = (ti.get("file_path") or "").replace("\\", "/")
text = ti.get("content") or ti.get("new_string") or ""


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


if re.search(r"(^|/)certs/sealed-secrets-pub\.pem$", path):
    sys.exit(0)  # the public cert is meant to be committed

if re.search(r"(\.pem|\.key|\.age)$|(^|/)(k3s\.yaml|[^/]*kubeconfig[^/]*)$", path, re.I):
    deny(
        f"Refusing to write '{path}': key/credential files must never be created in this repo "
        "(they are git-ignored but easy to leak). Keep them outside the working tree."
    )

if re.search(r"(^|/)(apps|infrastructure|fleet)/.*\.ya?ml$", path, re.I) and re.search(
    r"(?m)^kind:\s*Secret\s*$", text
):
    deny(
        f"Refusing to write a plaintext Kubernetes Secret into '{path}'. Only SealedSecrets may be "
        "committed: seal it with scripts/seal.sh or the Sealed Secrets web UI "
        "(https://sealed-secrets-web.k3s-node.home) and save the output as *.sealed.yaml. "
        "See docs/secrets.md."
    )

sys.exit(0)
