#!/usr/bin/env python3
"""Update the "Shipped in" footer on backport candidate issues.

Triggered by the shipped-in-footer GH Action on `release/*` tag push. For
every UUID in the new manifest, locate the backport candidate issue (search by
UUID in body) and rewrite the body's footer between sentinel comments.

Design doc §5.4.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

from _paths import add_repo_arg, ceph_repo, issues_repo

SENTINEL_START = "<!-- shipped-in:start -->"
SENTINEL_END = "<!-- shipped-in:end -->"
SENTINEL_RE = re.compile(rf"{re.escape(SENTINEL_START)}.*?{re.escape(SENTINEL_END)}", re.DOTALL)


def parse_tag(tag_name: str) -> str:
    # `release/<product>-v19.2.3-fasttrack-10` -> `19.2.3-fasttrack-10`
    return tag_name.split("-v", 1)[-1]


def find_manifest(repo: Path, version: str) -> Path:
    p = repo / "release-management" / f"MANIFEST-{version}.yaml"
    if not p.exists():
        sys.exit(f"manifest not found: {p}")
    return p


def search_issue_by_uuid(issues_slug: str, uuid: str) -> int | None:
    """Locate the backport-candidate issue containing this UUID in its body.

    Restricted to the tooling + issues repo where candidate issues actually
    live (design doc §5.1). Using a global `gh search` could otherwise match
    unrelated mentions of the same UUID in other repos in the same org.
    """
    out = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            issues_slug,
            "--search",
            uuid,
            "--state",
            "all",
            "--limit",
            "5",
            "--json",
            "number,body",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for item in json.loads(out):
        if uuid in (item.get("body") or ""):
            return item["number"]
    return None


def get_issue_body(issues_slug: str, num: int) -> str:
    return subprocess.run(
        [
            "gh",
            "issue",
            "view",
            str(num),
            "--repo",
            issues_slug,
            "--json",
            "body",
            "-q",
            ".body",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def set_issue_body(issues_slug: str, num: int, body: str) -> None:
    subprocess.run(
        ["gh", "issue", "edit", str(num), "--repo", issues_slug, "--body", body],
        check=True,
    )


def build_footer(version: str, previous_versions: list[str], previous_backport: str | None) -> str:
    lines = [SENTINEL_START, "## Shipped in", ""]
    if not previous_versions:
        lines.append(f"- {version} (first)")
    else:
        for v in previous_versions:
            lines.append(f"- {v}")
        lines.append(f"- {version}")
    if previous_backport:
        lines.extend(["", "## Carries forward from", "", f"- `{previous_backport}` (prior effort)"])
    lines.append(SENTINEL_END)
    return "\n".join(lines)


def replace_footer(body: str, footer: str) -> str:
    if SENTINEL_RE.search(body):
        return SENTINEL_RE.sub(footer, body)
    return body.rstrip() + "\n\n" + footer + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    add_repo_arg(ap)
    ap.add_argument("--tag", required=True, help="e.g. release/<product>-v19.2.3-fasttrack-10")
    args = ap.parse_args()

    repo = ceph_repo(args)
    issues_slug = issues_repo(repo)
    version = parse_tag(args.tag)
    manifest = yaml.safe_load(find_manifest(repo, version).read_text())

    updated = 0
    for bp in manifest.get("backports", []):
        uuid = bp["id"]
        issue_num = search_issue_by_uuid(issues_slug, uuid)
        if not issue_num:
            print(f"WARN: no backport-candidate issue found for {uuid}", file=sys.stderr)
            continue
        body = get_issue_body(issues_slug, issue_num)
        m = SENTINEL_RE.search(body)
        previous_versions: list[str] = []
        if m:
            # Pull "- v19.2.3-fasttrack-N" lines that are not the current version.
            for line in m.group(0).splitlines():
                if line.startswith("- ") and version not in line:
                    previous_versions.append(line[2:].split(" ", 1)[0])
        prev_uuid = bp.get("provenance", {}).get("previous_backport")
        footer = build_footer(version, previous_versions, prev_uuid)
        set_issue_body(issues_slug, issue_num, replace_footer(body, footer))
        updated += 1

    print(f"updated {updated} issue(s) on {issues_slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
