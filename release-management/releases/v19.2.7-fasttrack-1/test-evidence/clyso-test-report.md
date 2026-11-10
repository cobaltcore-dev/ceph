# CLYSO test report — cobaltcore-storage v19.2.7-fasttrack-1

Ceph version (build SHA): `ceph version 19.2.7-72-g68da157cc2d (68da157cc2d8b47409d2911b8c9c70d9c6eb1d39) squid (stable)`

## Production / dashboard observations

- Tests carried out on CLYSO's S3 production service, with a soak
  window from 2026-11-02 to 2026-11-09.
- Rollout was not smooth. On 2026-11-02 the OSDs started flapping after
  the upgrade. The cause is a known bug, tracker issue 80440: cephadm
  compares the keyring file as text, and `ceph-bluestore-tool
  prime-osd-dir` rewrites that file in a different format on every OSD
  start. The key itself is unchanged, but the text never matches, so
  cephadm treats every OSD reconfiguration as a keyring rotation and
  stops and restarts the OSD. Any operation that reconfigures the OSDs,
  for example adding or removing a monitor, therefore restarts all of
  them in sequence.
- The flapping was stopped on the affected cluster by a patch applied
  there. That patch is not part of this release build. The tracker issue
  also documents a workaround that needs no patch: overwrite each OSD
  keyring file with the exact output of `ceph auth get osd.N`, owner
  `167:167`, mode `0600`. The workaround has to be reapplied after each
  OSD restart, because the tool rewrites the file again.
- The bug was introduced in 19.2.6. The squid backport was merged after
  the v19.2.7 tag, so it is not part of this release. See the "Known
  bugs" section below.
- There was also a cluster outage in the same period. As far as we can
  tell it is not related to the upgrade. The current assessment is that
  it was caused by internal datacenter activities, moving nodes to
  another rack.

## Known bugs

### cephadm: OSD restarts on every reconfiguration (https://tracker.ceph.com/issues/80440)

Affects every cephadm cluster with LVM BlueStore OSDs from 19.2.6
onwards, including this release. The squid backport
(https://tracker.ceph.com/issues/80803, commit `de8e9fdbef8`) was merged
32 commits after the v19.2.7 tag and is therefore not in this release.
It is expected in 19.2.8.

Effect: each OSD reconfiguration stops and restarts the OSD, so
operations that reconfigure all OSDs restart the whole cluster's OSDs
one after another.

Workaround: before an operation that triggers a reconfiguration,
overwrite each OSD keyring file with the exact output of `ceph auth get
osd.N` (owner `167:167`, mode `0600`), and reapply it after each OSD
restart.

### Monitor log acknowledgements are lost for daemons on a peon (https://tracker.ceph.com/issues/81604)

Daemons connected to a peon monitor never receive an `MLogAck`, so their
cluster-log queue grows without bound. On the monitors the unresolved
routed requests appear as permanent slow operations.

Two parts combine to produce this. An OSD that boots before it has the
real monmap sends cluster log entries with a zero fsid; the leader drops
them on the fsid check in `LogMonitor::prepare_log` without sending a
reply, so the peon keeps the routed request. The earlier workaround for
tracker issue 54489 (commit `1bf93fc10c6`, "LogMonitor: set no_reply for
forward MLog commands") then suppresses the acknowledgement for every
forwarded log message, not only for that path. Both are present in this
release; the squid backport (https://tracker.ceph.com/issues/82684, PR
73629) is not merged.

The tracker gives no workaround. Restarting an affected daemon clears
its queue, and the queue grows again while the daemon stays connected to
a peon.

### KMS cache

The two known bugs below have low risk. Neither bug changes stored data
or the result of a request that succeeds. Upstream PR
https://github.com/ceph/ceph/pull/73032 fixes both bugs. The PR is
under review, and this backport does not include it.

#### Slow shutdown (https://tracker.ceph.com/issues/81968)

radosgw shutdown can hang for up to 2 minutes. The TTL reaper is a
background task that removes expired cache entries. At shutdown,
radosgw sends a stop signal to the reaper. If the signal arrives
between the end of the reaper timer and the next reaper step, the
reaper does not see it. That window is very short. By default, the
timer ends once every 10 seconds (the smallest cache TTL).

If the reaper misses the stop signal, the `rgw_exit_timeout_secs` alarm
(default 2 minutes) or the systemd stop timeout ends the process. The
result is a rare slow restart. The valgrind leak report in the tracker
comes from the stuck reaper at exit. Memory does not grow while
radosgw runs.

#### No cache in a daemonized radosgw (https://tracker.ceph.com/issues/82031)

The KMS cache does not work in a daemonized radosgw. A daemonized
radosgw starts without `-f` and moves to the background with `fork()`.
This mode is uncommon. Standard deployment tools (e.g. Rook, cephadm)
start radosgw in the foreground.

If a thread reads a secret that a different thread cached, the read
fails. That request returns `ERR_INTERNAL_ERROR`, and the cache turns
itself off. After that, radosgw does one KMS lookup per request, as
before this feature.

To prevent this bug, start radosgw with `-f`. If you cannot use `-f`,
set `rgw_crypt_s3_kms_cache_enabled = false`.

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
