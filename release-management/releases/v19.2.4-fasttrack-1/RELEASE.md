---
release: cobaltcore-storage-v19.2.4-fasttrack-1
release_tag: release/cobaltcore-storage-v19.2.4-fasttrack-1
source_commit: 7ae8fa43fe686a59c437fb7a40f35cb5ada9472c
rc_tag: cut/v19.2.4-fasttrack-1-rc1

manifest_sha256: d0bc8424798e781de5c1e0557b3a0cd6c3c90d432529d1cc43554a01f6a9b8a0

artifact_digests:
  - kind: container-image
    ref: harbor.clyso.com/custom-ceph/ceph/ceph
    tag: cobaltcore-storage-v19.2.4-fasttrack-1
    digest: sha256:362537d9d98c78d79e8afeee1481c9607b37c8e229a55abb840abf691e49f885

release_engineer:
  github_handle: irq0

test_evidence:
  files:
    - release-management/releases/v19.2.4-fasttrack-1/test-evidence/clyso-test-report.md
    - release-management/releases/v19.2.4-fasttrack-1/test-evidence/rc-recovery-divergence.txt
  summary: |
    Tested by CLYSO per agreement. Production S3 rollout was smooth with no performance regressions observed in dashboards. Unit tests passed. Teuthology results match upstream. Rook integration passed against a semi-automated Minikube install with Keystone and Barbican; small-scale SSE-KMS benchmarks passed. Out of scope (covered by SAP): large-scale cluster tests, scalability benchmarks, additional regression tests of new features. See test-evidence/clyso-test-report.md for the full report.
---
