# CLYSO test report — cobaltcore-storage v19.2.4-fasttrack-1

Ceph version (build SHA): `ceph version 19.2.4-45-g7ae8fa43fe6 (7ae8fa43fe686a59c437fb7a40f35cb5ada9472c) squid (stable)`

## Production / dashboard observations

- Tests carried out on CLYSO's S3 production service.
- Rollout was smooth.
- Dashboards showed no performance regressions.
- Metrics showed a temporary loss of RGW and backend r/w traffic
  during the soak phase. The following RCA attributed this to
  unavailable RGWs due to to a cascading failure from another
  infrastructure component. All non-RGW services on the cluster did
  not show any anomaly during that incident.

## Unit tests

Passed

## Teuthology

- Running as successfully as the upstream tests.

## Rook

- Semi-automated Minikube Rook installation connected to Keystone and
  Barbican: tests passed.
- Small-scale SSE-KMS benchmarks using k6: passed.

## Out of scope (covered by SAP)

- Large-scale Ceph cluster tests
- Scalability tests
- Benchmarks
- Additional regression tests of the new features

## Operational guidance (from announcement)

Please be kindly reminded to ensure you have a backup before roll-out.
While the software is designed for high reliability and performance,
please note that CLYSO does not provide a guarantee against data loss.
Data integrity and regular backups remain the sole responsibility of
the customer.
