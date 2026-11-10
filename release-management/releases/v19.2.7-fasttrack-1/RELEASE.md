---
# Pre-filled by `just promote`. Edit only the prose `summary:` if needed.
# Tag names are convenience labels. Authoritative fields are SHAs.
release: cobaltcore-storage-v19.2.7-fasttrack-1
release_tag: release/cobaltcore-storage-v19.2.7-fasttrack-1
source_commit: 68da157cc2d8b47409d2911b8c9c70d9c6eb1d39   # the RC commit R; embedded in binaries
rc_tag: cut/v19.2.7-fasttrack-1-rc3                 # label only; SHA is source_commit

manifest_sha256: 45867d6555993fc4764234aa067bf700eae55609d707e875dac52048a7f6e953

artifact_digests:
  - kind: container-image
    ref: harbor.clyso.com/c-customers/cobaltcore/ceph/ceph
    tag: 19.2.7-fasttrack-1
    digest: sha256:5123bac4cbc7ac2af1183cf20d0956882869a11118a22b505f6ea60f2dad8895

release_engineer:
  github_handle: s0nea

test_evidence:
  files:
    - release-management/releases/v19.2.7-fasttrack-1/test-evidence/clyso-test-report.md
    - release-management/releases/v19.2.7-fasttrack-1/test-evidence/image-derivation.md
  summary: |
    Tested by CLYSO per agreement, with a production S3 soak window from
    2026-11-02 to 2026-11-09.
    The rollout was not smooth: the OSDs started flapping after the upgrade,
    caused by a known 19.2.6 bug (cephadm, tracker 80440) whose squid backport
    was merged after the v19.2.7 tag and is therefore not in this release. A
    workaround is documented and the fix is expected in 19.2.8.
    Three further known bugs are carried and documented in the report:
    lost monitor log acknowledgements for daemons on a peon (81604), and two
    low-risk KMS cache bugs (81968, 82031).
    Unit tests passed. Teuthology results match upstream. Rook integration
    passed against a semi-automated Minikube install with Keystone and
    Barbican; small-scale SSE-KMS benchmarks passed. Out of scope (covered by
    SAP): large-scale cluster tests, scalability benchmarks, additional
    regression tests of new features. See test-evidence/clyso-test-report.md
    for the full report.
---
