#!/usr/bin/env python3
"""Foundation-phase MANIFEST sanity check for the promote workflow.

Asserts the manifest is well-formed and that each artifact entry has a sha256
digest. A real implementation will call `skopeo` / `cosign verify` here.
"""

from __future__ import annotations

import argparse
import sys

import yaml

from _paths import add_repo_arg, ceph_repo


def main() -> int:
    ap = argparse.ArgumentParser()
    add_repo_arg(ap)
    ap.add_argument("--version", required=True, help="e.g. 19.2.3-fasttrack-10")
    args = ap.parse_args()

    repo = ceph_repo(args)
    manifest_path = repo / "release-management" / f"MANIFEST-{args.version}.yaml"
    if not manifest_path.exists():
        sys.exit(f"manifest not found: {manifest_path}")

    doc = yaml.safe_load(manifest_path.read_text())
    artifacts = doc["release"]["artifacts"]
    for a in artifacts:
        digest = a.get("digest") or a.get("sha256")
        if not digest:
            print(f"ERROR: artifact missing digest: {a}", file=sys.stderr)
            return 1
    print(f"verified {len(artifacts)} artifacts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
