#!/usr/bin/env python3
"""Static checks for this GitOps repo. Needs only PyYAML.  Usage: python scripts/lint.py

Enforces the conventions in CLAUDE.md / docs/. Errors fail the run; warnings are advisory.
Run it before committing; CI runs it on every push and pull request.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOMAIN = ".k3s-node.home"
ISSUER = "k3s-node-ca-issuer"
GITREPO_NAME = "github"  # name of the Fleet GitRepo; bundle names are <name>-<path with dashes>
BUNDLE_ROOTS = ("apps", "infrastructure")
UNPINNED_TAGS = {"latest", "stable", "main", "master", "edge", "nightly"}
WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet"}
NAMESPACED_IN_APPS = {
    "Deployment", "StatefulSet", "DaemonSet", "Service", "Ingress", "PersistentVolumeClaim",
    "NetworkPolicy", "ConfigMap", "LimitRange", "ResourceQuota", "SealedSecret",
}

errors: list[str] = []
warnings: list[str] = []


def err(path: Path | str, msg: str) -> None:
    errors.append(f"{Path(path).relative_to(ROOT) if isinstance(path, Path) else path}: {msg}")


def warn(path: Path | str, msg: str) -> None:
    warnings.append(f"{Path(path).relative_to(ROOT) if isinstance(path, Path) else path}: {msg}")


def load_docs(path: Path) -> list[dict]:
    try:
        return [d for d in yaml.safe_load_all(path.read_text(encoding="utf-8")) if isinstance(d, dict)]
    except yaml.YAMLError as e:
        err(path, f"invalid YAML: {e}")
        return []


def bundle_name(d: Path) -> str:
    return GITREPO_NAME + "-" + d.relative_to(ROOT).as_posix().replace("/", "-")


def bundle_dirs() -> list[Path]:
    out = []
    for top in BUNDLE_ROOTS:
        base = ROOT / top
        if base.is_dir():
            out += sorted(p for p in base.iterdir() if p.is_dir())
    return out


# ---------------------------------------------------------------- manifests
def check_bundles() -> set[str]:
    names = set()
    for d in bundle_dirs():
        fleet = d / "fleet.yaml"
        if not fleet.exists():
            err(d, "missing fleet.yaml (without it Fleet lumps this directory into a root bundle)")
            continue
        names.add(bundle_name(d))
        conf = (load_docs(fleet) or [{}])[0]
        helm = conf.get("helm") or {}
        if helm.get("chart") and helm.get("repo") and not helm.get("version"):
            err(fleet, "Helm chart must pin helm.version")
        if d.parent.name == "apps" and not conf.get("defaultNamespace"):
            err(fleet, "apps bundles must set defaultNamespace")
    return names


def check_app_manifests() -> None:
    for d in bundle_dirs():
        files = sorted(p for p in d.glob("*.yaml") if p.name != "fleet.yaml")
        docs = [(f, x) for f in files for x in load_docs(f)]
        fleet = (load_docs(d / "fleet.yaml") or [{}])[0] if (d / "fleet.yaml").exists() else {}
        default_ns = fleet.get("defaultNamespace")
        kinds = {x.get("kind") for _, x in docs}

        for f, x in docs:
            kind, meta = x.get("kind"), x.get("metadata") or {}
            if kind == "Secret":
                err(f, "plaintext Secret manifest; seal it (scripts/seal.sh or the web UI)")
            if f.name.endswith(".sealed.yaml") and kind != "SealedSecret":
                err(f, f"*.sealed.yaml must contain only SealedSecret (found {kind})")
            if kind == "SealedSecret" and not (x.get("spec") or {}).get("encryptedData"):
                err(f, "SealedSecret has no spec.encryptedData")
            if d.parent.name == "apps":
                if kind == "Namespace" and meta.get("name") != d.name:
                    err(f, f"namespace '{meta.get('name')}' should be named after the app directory '{d.name}'")
                if kind in NAMESPACED_IN_APPS and default_ns and meta.get("namespace") != default_ns:
                    err(f, f"{kind}/{meta.get('name')} namespace '{meta.get('namespace')}' != fleet defaultNamespace '{default_ns}'")
            if kind in WORKLOADS:
                check_workload(f, x)
            if kind == "Ingress":
                check_ingress(f, x)

        if d.parent.name == "apps":
            if "Deployment" in kinds or "StatefulSet" in kinds:
                if "NetworkPolicy" not in kinds:
                    err(d, "app runs a workload but has no NetworkPolicy")
                if "LimitRange" not in kinds or "ResourceQuota" not in kinds:
                    warn(d, "no LimitRange/ResourceQuota (see apps/uptime-kuma)")
            if "Namespace" not in kinds and (d / "namespace.yaml").exists() is False and kinds - {"SealedSecret"}:
                warn(d, "no namespace.yaml; relies on Fleet/Helm creating the namespace")


def check_workload(f: Path, x: dict) -> None:
    pod = ((x.get("spec") or {}).get("template") or {}).get("spec") or {}
    name = (x.get("metadata") or {}).get("name")
    for c in (pod.get("containers") or []) + (pod.get("initContainers") or []):
        image = c.get("image", "")
        last = image.rsplit("/", 1)[-1]
        if "@sha256:" in image:
            pass
        elif ":" not in last:
            err(f, f"{name}/{c.get('name')}: image '{image}' has no tag")
        elif last.split(":", 1)[1] in UNPINNED_TAGS:
            err(f, f"{name}/{c.get('name')}: image '{image}' uses a floating tag; pin a version")
    for c in pod.get("containers") or []:
        res = c.get("resources") or {}
        if not (res.get("requests") or {}).get("memory") or not (res.get("limits") or {}).get("memory"):
            err(f, f"{name}/{c.get('name')}: set resources.requests.memory and limits.memory")
        if not (res.get("requests") or {}).get("cpu"):
            err(f, f"{name}/{c.get('name')}: set resources.requests.cpu")
        for probe in ("readinessProbe", "livenessProbe"):
            if probe not in c:
                warn(f, f"{name}/{c.get('name')}: no {probe}")


def check_ingress(f: Path, x: dict) -> None:
    name = (x.get("metadata") or {}).get("name")
    spec = x.get("spec") or {}
    ann = (x.get("metadata") or {}).get("annotations") or {}
    if spec.get("ingressClassName") != "traefik":
        err(f, f"Ingress/{name}: ingressClassName must be 'traefik'")
    if ann.get("cert-manager.io/cluster-issuer") != ISSUER:
        err(f, f"Ingress/{name}: annotation cert-manager.io/cluster-issuer must be {ISSUER}")
    hosts = [r.get("host") for r in spec.get("rules") or []]
    tls_hosts = {h for t in spec.get("tls") or [] for h in t.get("hosts") or []}
    for h in hosts:
        if not h or not h.endswith(DOMAIN):
            err(f, f"Ingress/{name}: host '{h}' should end with {DOMAIN}")
        if h not in tls_hosts:
            err(f, f"Ingress/{name}: host '{h}' is not covered by spec.tls")


def check_dependencies(names: set[str]) -> None:
    files = [d / "fleet.yaml" for d in bundle_dirs() if (d / "fleet.yaml").exists()]
    files += list((ROOT / "docs" / "examples").glob("*fleet.yaml"))
    for f in files:
        conf = (load_docs(f) or [{}])[0]
        for dep in conf.get("dependsOn") or []:
            n = dep.get("name")
            # Bundles from other GitRepos (the private chart) are not in this repo.
            if n and n not in names and not n.startswith("messages-archiver-"):
                err(f, f"dependsOn '{n}' matches no bundle in this repo (known: {', '.join(sorted(names))})")


def check_gitrepo() -> None:
    f = ROOT / "fleet" / "gitrepo.yaml"
    if not f.exists():
        return
    conf = (load_docs(f) or [{}])[0]
    if (conf.get("metadata") or {}).get("name") != GITREPO_NAME:
        err(f, f"GitRepo name must be '{GITREPO_NAME}' (bundle names and dependsOn rely on it)")
    paths = set((conf.get("spec") or {}).get("paths") or [])
    if paths != set(BUNDLE_ROOTS):
        err(f, f"spec.paths must be exactly {sorted(BUNDLE_ROOTS)} (found {sorted(paths)}); empty paths makes a root bundle")


def check_repo_hygiene() -> None:
    for pat in ("*.pem", "*.key", "*.crt", "*kubeconfig*", "k3s.yaml", "*.age"):
        for p in ROOT.rglob(pat):
            rel = p.relative_to(ROOT).as_posix()
            if rel.startswith((".git/", "node_modules/")):
                continue
            if rel == "certs/sealed-secrets-pub.pem":  # public, encrypt-only
                continue
            err(rel, "key/credential-looking file in the repo working tree (must not be committed)")


# --------------------------------------------------------------------- docs
def slug(heading: str) -> str:
    s = re.sub(r"[`*_]", "", heading.strip().lower())
    s = re.sub(r"[^\w\- ]", "", s)
    return s.replace(" ", "-")


def anchors(md: Path) -> set[str]:
    out = set()
    in_code = False
    for line in md.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and (m := re.match(r"#{1,6}\s+(.*)", line)):
            out.add(slug(m.group(1)))
    return out


def check_docs() -> None:
    md_files = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
    link = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
    for md in md_files:
        text = re.sub(r"```.*?```", "", md.read_text(encoding="utf-8"), flags=re.S)
        for target in link.findall(text):
            if re.match(r"[a-z]+:", target):
                continue
            path_part, _, frag = target.partition("#")
            dest = md if not path_part else (md.parent / path_part).resolve()
            if not dest.exists():
                err(md, f"broken link: {target}")
            elif frag and dest.suffix == ".md" and frag not in anchors(dest):
                err(md, f"broken anchor: {target}")

    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    for md in sorted((ROOT / "docs").glob("*.md")):
        if md.name != "README.md" and md.name not in index:
            err(md, "not listed in docs/README.md")
    for d in (ROOT / "apps").iterdir() if (ROOT / "apps").is_dir() else []:
        if d.is_dir() and f"apps/{d.name}" not in index:
            err(ROOT / "docs" / "README.md", f"app 'apps/{d.name}' missing from the Apps table")


def main() -> int:
    names = check_bundles()
    check_app_manifests()
    check_dependencies(names)
    check_gitrepo()
    check_repo_hygiene()
    check_docs()
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"ERROR:   {e}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s); {len(names)} bundles checked.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
