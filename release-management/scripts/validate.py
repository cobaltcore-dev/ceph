#!/usr/bin/env python3
"""Validate release-management/backports/*.md and (optionally) release-branch graph shape.

Two modes:
  validate.py                       File-level: schema + UUID uniqueness + filename match.
  validate.py --base=<ref>          + branch-level: merge-commit shape + first-parent graph.

All trailer reads go through `git interpret-trailers --parse`. No regex.

Exit codes: 0 OK, 1 errors. Warnings print to stderr but do not change exit code.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import jsonschema
import yaml

from _paths import add_repo_arg, backports_dir, ceph_repo, schema_path

UUID_V7_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


# ---------- helpers ----------


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], capture_output=True, text=True, cwd=repo, check=True)
    return out.stdout


def parse_trailers(repo: Path, message: str) -> dict[str, list[str]]:
    """Parse git commit-message trailers via `git interpret-trailers --parse`.

    Returns a dict mapping trailer key (case-preserved) to list of values.
    """
    out = subprocess.run(
        ["git", "interpret-trailers", "--parse"],
        input=message,
        capture_output=True,
        text=True,
        cwd=repo,
        check=True,
    ).stdout
    trailers: dict[str, list[str]] = {}
    for line in out.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        trailers.setdefault(k.strip(), []).append(v.strip())
    return trailers


def read_frontmatter(path: Path) -> dict:
    txt = path.read_text()
    m = FRONTMATTER_RE.match(txt)
    if not m:
        raise ValueError(f"{path}: no YAML frontmatter")
    return yaml.safe_load(m.group(1))


# ---------- file-level checks ----------


def check_files(repo: Path, errors: list[str]) -> dict[str, dict]:
    """Validate every release-management/backports/*.md (excl. README/RISK-RUBRIC).

    Returns {uuid: frontmatter}.
    """
    schema = json.loads(schema_path().read_text())
    by_uuid: dict[str, dict] = {}
    uuid_counts: Counter[str] = Counter()

    bp_dir = backports_dir(repo)
    md_files = sorted(p for p in bp_dir.glob("*.md") if p.stem not in {"README", "RISK-RUBRIC"})
    for path in md_files:
        stem = path.stem
        if not UUID_V7_RE.match(stem):
            errors.append(f"{path.name}: filename stem is not a UUIDv7")
            continue
        try:
            fm = read_frontmatter(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        try:
            jsonschema.validate(fm, schema)
        except jsonschema.ValidationError as exc:
            # `REPLACE_ME` is the scaffold sentinel from `just backport new`.
            # Recognise it and emit a domain-language message in addition to
            # the raw schema error; the file is otherwise valid markdown so
            # the schema message alone ("'REPLACE_ME' does not match
            # '^[0-9a-f]{40}$'") gives no hint about what to do.
            instance = exc.instance
            hint = ""
            if isinstance(instance, str) and "REPLACE_ME" in instance:
                hint = (
                    " — this is the `just backport new` scaffold sentinel; "
                    "fill it in per release-management/backports/RISK-RUBRIC.md"
                )
            elif isinstance(instance, list) and any(
                isinstance(x, str) and "REPLACE_ME" in x for x in instance
            ):
                hint = (
                    " — `REPLACE_ME` left over from `just backport new`; "
                    "replace with the real value(s) per RISK-RUBRIC.md"
                )
            errors.append(f"{path.name}: schema: {exc.message} (at {list(exc.path)}){hint}")
            continue

        if fm["id"] != stem:
            errors.append(f"{path.name}: frontmatter id ({fm['id']}) != filename stem ({stem})")

        uuid_counts[fm["id"]] += 1
        by_uuid[fm["id"]] = fm

    for uid, n in uuid_counts.items():
        if n > 1:
            errors.append(f"UUID {uid} appears in {n} files")

    return by_uuid


# ---------- branch-level checks ----------


def first_parent_commits(repo: Path, base: str, head: str = "HEAD") -> list[str]:
    out = git(repo, "log", "--first-parent", "--format=%H", f"{base}..{head}")
    return out.split()


def parents_of(repo: Path, sha: str) -> list[str]:
    return git(repo, "show", "--no-patch", "--format=%P", sha).split()


def commit_message(repo: Path, sha: str) -> str:
    return git(repo, "show", "--no-patch", "--format=%B", sha)


def commit_subject(repo: Path, sha: str) -> str:
    return git(repo, "show", "--no-patch", "--format=%s", sha).strip()


def files_introduced_by_merge(repo: Path, sha: str) -> list[str]:
    """Files added in the second-parent ancestry of a merge commit (relative to first parent)."""
    out = git(repo, "diff", "--name-only", "--diff-filter=A", f"{sha}^1", sha)
    return [line for line in out.splitlines() if line]


def check_branch(
    repo: Path, base: str, by_uuid: dict[str, dict], errors: list[str], warnings: list[str]
) -> None:
    head_shas = first_parent_commits(repo, base)
    seen_uuids: set[str] = set()
    for sha in head_shas:
        parents = parents_of(repo, sha)
        msg = commit_message(repo, sha)
        subject = commit_subject(repo, sha)
        if len(parents) == 1:
            if not subject.startswith("release:"):
                errors.append(
                    f"{sha[:10]}: non-merge commit on first-parent without 'release:' subject prefix"
                )
            continue
        if len(parents) > 2:
            errors.append(f"{sha[:10]}: octopus merge ({len(parents)} parents)")
            continue
        # 2 parents — must be a backport merge.
        trailers = parse_trailers(repo, msg)
        if "Backport-Id" not in trailers and "Backport-Update" not in trailers:
            errors.append(f"{sha[:10]}: merge commit missing Backport-Id / Backport-Update trailer")
            continue
        if "Backport-PR" not in trailers:
            errors.append(f"{sha[:10]}: merge commit missing Backport-PR trailer")
        uuid_values = trailers.get("Backport-Id") or trailers.get("Backport-Update") or [""]
        uuid = uuid_values[0]
        if not UUID_V7_RE.match(uuid):
            errors.append(f"{sha[:10]}: Backport-Id/Update trailer is not a UUIDv7: {uuid!r}")
            continue

        if "Backport-Id" in trailers:
            added = [
                p
                for p in files_introduced_by_merge(repo, sha)
                if p.startswith("release-management/backports/")
            ]
            if len(added) != 1:
                errors.append(
                    f"{sha[:10]}: backport merge must add exactly 1 release-management/backports/<uuid>.md "
                    f"(added: {added})"
                )
                continue
            added_uuid = Path(added[0]).stem
            if added_uuid != uuid:
                errors.append(f"{sha[:10]}: Backport-Id ({uuid}) != filename UUID ({added_uuid})")
                continue

            seen_uuids.add(uuid)

            fm = by_uuid.get(uuid)
            if fm and band_for(fm) == "high":
                # Soft enforcement (design doc §6 item 10).
                warnings.append(
                    f"{sha[:10]}: risk.band==high; verify QA-lead approval was recorded on the PR"
                )

    tree_uuids = set(by_uuid)
    orphaned = tree_uuids - seen_uuids
    if orphaned:
        errors.append(
            "tree has release-management/backports/<uuid>.md not reachable from any backport-merge commit "
            f"on the first-parent history: {sorted(orphaned)}"
        )


# ---------- risk band (also used by render.py) ----------

BLAST_W = {"cosmetic": 1, "availability": 2, "data-loss": 3}
CONFLICT_W = {"clean": 1, "trivial": 2, "substantive": 3}
COVERAGE_W = {"strong": 1, "partial": 2, "weak": 3}
UPSTREAM_W = {
    "merged-stable": 1,
    "merged-main": 1,
    "approved-open": 2,
    "open-in-review": 3,
    "downstream-only": 3,
}


def upstream_weight(fm: dict) -> int:
    if fm["provenance"]["type"] == "other":
        return 3
    return UPSTREAM_W[fm["provenance"]["upstream_pr_state"]]


def risk_total(fm: dict) -> int:
    r = fm["risk"]
    return BLAST_W[r["blast"]] + CONFLICT_W[r["conflict"]] + COVERAGE_W[r["coverage"]] + upstream_weight(fm)


def band_for(fm: dict) -> str:
    total = risk_total(fm)
    if total <= 6:
        return "low"
    if total <= 9:
        return "medium"
    return "high"


# ---------- main ----------


def main() -> int:
    ap = argparse.ArgumentParser()
    add_repo_arg(ap)
    ap.add_argument(
        "--base",
        help="Branch-level check: walk first-parent commits from <ref>..HEAD. "
        "Typically the upstream tag the release/effort branch was cut from.",
    )
    args = ap.parse_args()

    repo = ceph_repo(args)
    errors: list[str] = []
    warnings: list[str] = []

    by_uuid = check_files(repo, errors)

    if args.base:
        check_branch(repo, args.base, by_uuid, errors, warnings)

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if errors:
        return 1
    print(f"OK — {len(by_uuid)} backport file(s) validated", end="")
    if args.base:
        print(f"; graph from {args.base}..HEAD clean", end="")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
