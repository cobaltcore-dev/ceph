"""Shared path resolution.

Two distinct roots:

- `relenor_root()` — this tooling checkout. Schemas, Jinja templates, and the
  RISK-RUBRIC live here. Read-only at runtime.
- `ceph_repo(args)` — the *external* Ceph downstream working tree. Backport
  files, manifests, RELEASE.md records, and the per-instance
  `release-config.yaml` live there. Scripts mutate this tree.

A script's working set always splits along that boundary: input metadata
(schema, template) from relenor; output artifacts (manifest, files) into the
ceph repo.

Specifying the ceph repo:

1. `--repo=<path>` CLI flag (highest precedence)
2. `CEPH_REPO=<path>` environment variable
3. Otherwise: hard error. No silent default — mutating the wrong tree is the
   exact failure mode this split is meant to prevent.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

CEPH_REPO_ENV = "CEPH_REPO"


def relenor_root() -> Path:
    """Path to the checkout containing this script.

    Dual-mode: when invoked from relenor it returns the relenor root; when
    `_paths.py` is shipped to the ceph fork (under `release-management/scripts/`)
    it returns the ceph-fork root and `ceph_repo()` resolves to the same path.
    Both setups place the schema, templates, and backport tree at the same
    relative locations, so no special-casing is needed.
    """
    return Path(__file__).resolve().parents[2]


def add_repo_arg(parser: argparse.ArgumentParser) -> None:
    """Register the --repo flag on a script's argparser."""
    parser.add_argument(
        "--repo",
        help=f"Path to the Ceph downstream working tree (default: ${CEPH_REPO_ENV})",
    )


def ceph_repo(args: argparse.Namespace) -> Path:
    """Return the absolute path to the Ceph downstream working tree.

    Resolution: `--repo` flag → `$CEPH_REPO` env var → error.
    """
    candidate = getattr(args, "repo", None) or os.environ.get(CEPH_REPO_ENV)
    if not candidate:
        sys.exit(f"error: ceph repo not specified. Pass --repo=<path> or set ${CEPH_REPO_ENV}.")
    path = Path(candidate).expanduser().resolve()
    if not path.is_dir():
        sys.exit(f"error: {path} is not a directory")
    if not (path / ".git").exists():
        sys.exit(f"error: {path} is not a git checkout")
    return path


# --- ceph-repo paths (mutated by tooling at runtime) ---


def backports_dir(repo: Path) -> Path:
    """Per-backport <uuid>.md files. Lives in the **ceph** repo."""
    return repo / "release-management" / "backports"


def releases_dir(repo: Path) -> Path:
    """Per-release directories (RELEASE.md, test-evidence/). Lives in the **ceph** repo."""
    return repo / "release-management" / "releases"


def config_path(repo: Path) -> Path:
    """`release-config.yaml`. Lives in the **ceph** repo (per-instance configuration)."""
    return repo / "release-management" / "release-config.yaml"


def issues_repo(repo: Path) -> str:
    """The `<org>/<repo>` GH slug of the tooling + issues repo.

    Read from `release-config.yaml` in the ceph repo. This is where
    backport-candidate issues, release-tracking issues, and the effort
    milestone live (design doc §5.1, §5.2). Distinct from `downstream_repo`,
    which is the ceph fork itself.
    """
    cfg = yaml.safe_load(config_path(repo).read_text())
    slug = cfg.get("issues_repo")
    if not slug:
        sys.exit(
            f"error: {config_path(repo)} is missing 'issues_repo'. "
            f"Add it (e.g. `issues_repo: cobaltcore-dev/cloud-storage`); "
            f"see release-config.yaml.example."
        )
    return slug


# --- relenor-checkout paths (read-only at runtime) ---


def schema_path() -> Path:
    """Backport-file JSON schema. Lives in the **relenor** checkout."""
    return relenor_root() / "release-management" / "backports" / "schema.json"


def manifest_schema_path() -> Path:
    """Manifest JSON schema. Lives in the **relenor** checkout."""
    return relenor_root() / "release-management" / "manifest-schema.json"


def template_dir() -> Path:
    """Jinja templates (RELEASE-NOTES.md.j2, etc.). Lives in the **relenor** checkout."""
    return relenor_root() / "release-management" / "templates"


def release_template_path() -> Path:
    """`RELEASE.md` template used by promote.py. Lives in the **relenor** checkout."""
    return relenor_root() / "release-management" / "releases" / "_TEMPLATES" / "RELEASE.template.md"
