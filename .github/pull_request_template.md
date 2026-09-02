<!--
Backport PR checklist. CI runs `just validate` and enforces what matters; this
is a reminder for the author.
-->

<!--
Cross-repo `Closes` — the backport-candidate issue lives in the
tooling + issues repo, not on this ceph fork. Fill in the org/repo
your instance uses; the example below assumes cobaltcore-dev.

GitHub's auto-close only fires if you have write on both repos.
`just merge-backport` will close the linked issue via the API on a
successful merge regardless of whether auto-close fires, so this
line's purpose is visual linkage + audit trail.
-->

Closes cobaltcore-dev/cloud-storage#<!-- backport candidate issue number -->

## Backport file

- [ ] `release-management/backports/<uuid>.md` added (or updated) by this PR
- [ ] `id` in frontmatter matches the filename stem
- [ ] `provenance.upstream_prs` set (or `provenance.type: other` with an `other:` block)

## Stage-B risk (filled per `release-management/backports/RISK-RUBRIC.md`)

- [ ] `blast` — cosmetic / availability / data-loss
- [ ] `conflict` — clean / trivial / substantive
- [ ] `coverage` — strong / partial / weak
- [ ] Risk-notes paragraph in the prose section (required for `high` band)

## Merge

Land this via `just merge-backport PR=<N>` — do not click the green merge button. The just recipe
constructs the merge commit's `Backport-Id` trailer.
