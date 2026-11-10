# cobaltcore-storage 19.2.7-fasttrack-1

**Upstream base:** 19.2.7 (v19.2.7)
**Downstream tag:** release/cobaltcore-storage-v19.2.7-fasttrack-1
**Branch:** squid-19.2.7-cobaltcore-storage

## Built artifacts

- **container-image**: `harbor.clyso.com/c-customers/cobaltcore/ceph/ceph:19.2.7-fasttrack-1` (`sha256:5123bac4cbc7ac2af1183cf20d0956882869a11118a22b505f6ea60f2dad8895`)
- **container-image**: `ghcr.io/cobaltcore-dev/ceph:cobaltcore-storage-v19.2.7-fasttrack-1` (`sha256:5123bac4cbc7ac2af1183cf20d0956882869a11118a22b505f6ea60f2dad8895`)

## Verification

See `release-management/releases/v19.2.7-fasttrack-1/RELEASE.md` for the authoritative build and
test record (source commit, artifact digests, RE identity, full test
summary) and `release-management/releases/v19.2.7-fasttrack-1/test-evidence/` for raw
test artifacts.

## New features

### IAM / Bucket Policy: Keystone role and user ID support

Allows Keystone role names and user IDs to be injected as `keystone:role` and
`keystone:userid` condition keys in S3 bucket policies, enabling role-based and
per-user access control via standard IAM policy conditions.

Note: do not use `StringNotEquals` or the other "NotEquals" conditions in this
release; see the known limitation below.

#### Related tickets

- cobaltcore-dev/cloud-storage#611
- cobaltcore-dev/cloud-storage#467
- cobaltcore-dev/cloud-storage#380
- cobaltcore-dev/cloud-storage#372

#### Behavior change

Requests authenticated via Keystone now expose two additional IAM policy
condition keys: `keystone:role` (one entry per role, lowercased) and
`keystone:userid` (the Keystone user UUID). Requests not authenticated via
Keystone are unchanged, and no existing policy changes behaviour.

### Known limitation: "NotEquals" conditions

In this release, `StringNotEquals` and the other "NotEquals" conditions behave
differently than they do in Ceph main. Here a condition matches when the value
differs from any one of the listed values, instead of only when it differs from
all of them. This means a rule such as "deny anyone who is not an admin" will
also deny a user who is an admin, if that user holds other roles as well. The
behaviour was corrected upstream in commit
`225241d6ae6fc43fd6515910a5450006006d4ce0`, which exists only on the main branch
and is not part of squid. Until that change is included, avoid "NotEquals"
conditions in bucket policies and write the rule using `StringEquals` instead.

This affects nearly all Keystone users, because Keystone assigns implied roles
automatically — a user granted only `member` typically also holds `reader`.

### Two further points for policy authors

Role names in policies are case-sensitive. Roles are lowercased on the way into
the policy environment, so how the role is spelled in Keystone does not matter,
but the value typed in the policy is compared exactly. A policy containing
`"TestRole"` never matches and gives no warning. Write role names in lower case,
or use `StringEqualsIgnoreCase`.

Rules that distinguish between users of the same project must be written as
`Deny`. All users in an OpenStack project share a single RGW account, so each is
an owner of buckets created there, and owners are not restricted by `Allow`
conditions. `Deny` statements do apply to owners and discriminate correctly.

#### Risks

**blast: cosmetic** — purely additive. Two new condition keys are populated for
Keystone-authenticated requests. No existing condition key, policy or auth path
changes meaning, and non-Keystone requests are untouched.

**conflict: substantive** — the cherry-picks did not apply mechanically.
Upstream wrote this PR against a tree that already had `AuthInfo::keystone_user`
and `AuthInfo::keystone_scope`, added by an unrelated upstream change
(3180812e541, "rgw: Add Keystone scope information to ops logging"). This branch
has neither, and `src/rgw/rgw_keystone_scope.h` does not exist here at all. Both
fields and the `build_scope_info()` call were dropped during resolution; only
`keystone_roles` and `keystone_user_id` were taken. Verified afterwards by
diffing `AuthInfo` against upstream/squid: the only differences are the two new
members, two trailing defaulted constructor parameters, and two initialiser
entries. Because the new parameters are trailing and defaulted, every existing
caller compiles unchanged.

**coverage: partial** — 39/39 unit tests pass, and 11/11 live end-to-end checks
pass against a real Keystone, covering both keys for single-role, multi-value,
wildcard and per-user matching. However, upstream's
`KeyStoneRoleNotStringEquals` test was deliberately dropped: it asserts the
fixed NotEquals behaviour, which this branch does not have. The `ConditionTest`
fixture it depends on was added by hand rather than taken from upstream, as it
belongs to the same absent upstream PR.

The NotEquals fault described below is pre-existing on squid and is not
introduced by this backport. The upstream fix (c4e750e6767, 225241d6ae6,
c8372be8800) is tracked as a separate backport candidate, since it changes
evaluation of every condition key and needs its own review.

#### Upgrade notes

None.

**Upstream PRs:** https://github.com/ceph/ceph/pull/67752

### Write Lock Lua Extensions

RGW Lua scripting extensions to allow "Write Lock" feature

New postAuth Lua hook point that runs after authentication / authorization but before the operation executes.
Lua scripts can now read bucket tags.
Lua scripts can abort request processing.

#### Related tickets

- cobaltcore-dev/cloud-storage#613
- cobaltcore-dev/cloud-storage#310

#### Behavior change

A new postAuth Lua hook point is available. Scripts can read bucket
tags and abort request processing. Lua is inactive out of the box (no
scripts are uploaded by default).

#### Risks

The postAuth hook runs on every request. A slow or buggy Lua script will add latency to all S3 operations.

#### Upgrade notes

(Operator instructions, if any.)

**Upstream PRs:** https://github.com/ceph/ceph/pull/67219, https://github.com/ceph/ceph/pull/67548, https://github.com/ceph/ceph/pull/66065

### Keystone Project RO/Viewer role + Implicit Deny

This feature introduces two new config options: `rgw_keystone_accepted_project_reader_roles` and `rgw_keystone_implicit_deny_roles`.

- `rgw_keystone_accepted_project_reader_roles`:  A reader role, but can be granted more permissions by using bucket policy and condition keys, keystone:userid and keystone:role.
- `rgw_keystone_implicit_deny_roles`: No permissions by default, but authenticated by keystone. Similar to reader role above, more permission can be granted using bucket policy and conditions, keystone:userid and keystone:role

#### Related tickets

- cobaltcore-dev/cloud-storage#616
- cobaltcore-dev/cloud-storage#468
- cobaltcore-dev/cloud-storage#511

#### Behavior change

Two new configuration options, both defaulting to empty, so nothing changes
until an operator sets them.

- `rgw keystone accepted project reader roles` — a role listed here admits the
  user on its own and caps it to `RGW_PERM_READ | RGW_PERM_READ_ACP` within its
  own Keystone project. Reads and configuration inspection are allowed; writes
  are refused.
- `rgw keystone implicit deny roles` — a role listed here admits the user with
  no implicit permissions at all. Such a user cannot even list its project's
  buckets without an explicit policy grant.

For both tiers the most permissive accepted role wins, so a user that also
holds `admin` or a plain accepted role such as `member` receives full control.
Both caps are a floor, not a ceiling: a bucket policy naming the user by
`keystone:userid` or `keystone:role` grants access for that bucket only.

Refused up front for a capped identity regardless of policy: bucket creation,
Swift account-metadata writes, and STS `AssumeRole` (which would replace the
identity with a role identity carrying no permission mask, discarding the cap).

The caps do not apply to the librgw/NFS-Ganesha frontend, to Keystone users
associated with an RGW account (governed entirely by IAM policy), or to
`radosgw-admin` and the admin REST API.

#### Risks

**blast: availability** — the two new roles are off by default, so nothing
changes for existing users until an operator configures them. The reason this
is not rated cosmetic is that the change reworks how permissions are worked out
for *every* Keystone user, not only for users of the new roles. If that went
wrong, people could lose access they should have. That is recoverable and no
data is at risk, which is why it is availability rather than data-loss.

**conflict: substantive** — the upstream changes did not apply cleanly to this
release. Upstream has since gained several Keystone and S3 features that are
not in squid, and the patches were written on top of them. Five conflicts had
to be resolved by hand, each time keeping only the parts belonging to this
feature and leaving the unrelated newer features out. This is the kind of
change where the downstream result deserves review in its own right, not just a
check that it matches upstream.

**coverage: strong** — 88 checks in total, none failing: some against the
code on its own, the rest against a running gateway talking to a real Keystone
server. What was checked:

- A user with only a reader role can read, and cannot write. Every storage
  operation a client can make was tried, one by one, including bucket settings
  and notifications: reads succeeded, writes were refused.
- A user with only an implicit-deny role can do nothing at all, not even list
  the buckets in its own project.
- A user holding a normal role such as `member`, or `admin`, still has full
  control. Nothing changes for existing users.
- A bucket policy naming a capped user can give it access it would not
  otherwise have, including write access for a reader. This was checked with a
  policy naming the user directly and with a policy naming their role.
- That extra access is limited to what the policy says: another user is still
  refused, the same user is still refused on a different bucket, and removing
  the policy puts the restriction back.
- The Keystone condition keys added by the earlier backport still work.

Four of the upstream tests could not be carried over, because they rely on
internals that this release does not have. What they checked is covered by the
checks above against the running gateway. Restoring them would mean backporting
a further upstream change unrelated to this feature; a note in the test file
records which one.

**Taken ahead of upstream.** The upstream change is approved but not yet
merged. If it is revised before it lands, this backport and the final upstream
version could differ, and the next upstream sync may need rework.

#### Upgrade notes

No migration and no action required on upgrade. Both options default to empty
and the behaviour of existing Keystone users is unchanged.

To adopt the feature, add the Keystone role name to the relevant option:

    rgw keystone accepted roles = member
    rgw keystone accepted project reader roles = objectstore_viewer

Assign a user *only* the reader role to keep it read-only; any additional
accepted role restores full control. Setting `rgw keystone implicit tenants =
true` is recommended, as the documentation notes.

**Upstream PRs:** https://github.com/ceph/ceph/pull/70372

### KMS Cache

Adds a secure in-memory cache for SSE-KMS encryption keys retrieved from Barbican (or other KMS backends), eliminating redundant round-trips on repeated access to the same encrypted objects. Uses a new SIEVE-based eviction cache (WebCache) and stores decrypted secrets in the Linux kernel keyring.
Please refer to the Ceph documentation on how to configure this feature.

#### Related tickets

- cobaltcore-dev/cloud-storage#617
- cobaltcore-dev/cloud-storage#125

#### Behavior change

Repeated SSE-KMS access no longer hits the KMS backend on every
request; decrypted secrets are cached in-memory and in the Linux
kernel keyring. KMS-cache is ON out of the box.

#### Risks

- TTLs mean that a deleted or rotated Barbican key won't be immediately reflected.
- New async primitives (async::call_once) and the WebCache are
  significant new library code shipping for the first time.
- Cache size tuning and system wide keyring quota adjustment needed
  for production workloads (refer to the docs).

#### Upgrade notes

Feature flag: rgw_crypt_s3_kms_cache_enabled. Set false to disable
caching entirely and revert to per-request KMS lookups.

**Upstream PRs:** https://github.com/ceph/ceph/pull/61256, https://github.com/ceph/ceph/pull/58229, https://github.com/ceph/ceph/pull/57188

### Add Keystone scope information to ops logging -> audit logs

Add OpenStack Keystone authentication scope information to RGW operations logs.
It enables audit trails for multi-tenant and compliance-sensitive environments, by adding the keystone_scope field (project, user, domain, roles, application credentials) to RGW ops logs.

#### Related tickets

- cobaltcore-dev/cloud-storage#619
- cobaltcore-dev/cloud-storage#335

#### Behavior change

Keystone scope (project, domain, roles) appears in RGW ops logs. This
feature is OFF by default.

#### Risks

Scope logging with `rgw_keystone_scope_include_user=true` writes
human-readable usernames to ops logs, which may have GDPR / privacy
implications.

#### Upgrade notes

- `rgw_keystone_scope_enabled` - enable Keystone scope in the ops log

**Upstream PRs:** https://github.com/ceph/ceph/pull/66111, https://github.com/ceph/ceph/pull/68627

### rate limit "retry after" header

customer request

#### Related tickets

- cobaltcore-dev/cloud-storage#620
- todo

#### Behavior change

S3 responses rejected with `503 ERR_RATE_LIMITED` now carry a `Retry-After`
header with the estimated number of seconds until the caller can make a rquest
again.

#### Risks

**blast: availability.** The commit adds more than just a new header. The
commit also rewrites the accept/reject decision. It runs for every request of
a user or bucket with rate limiting enabled. A bug here means requests are 
wrongly rejected, or wrongly let through and the cluster loses the protection 
the limit is meant to give. Nothing is written to disk, so no data is at risk.
Clusters without rate limiting are unaffected.

**conflict: substantive.** The cherry-pick without its two parents (91e9f00,
dae572d) raised some conflicts documented as part of the commit message.
The most important one, unlike `main`, the config option
`rgw_ratelimit_interval` does not exist on this branch and was replaced
by `RateLimiterEntry::ratelimit_interval_seconds = 60`. That constant matches
the default value.

**coverage: partial.** The new `compute_delay()` helper has a dedicated unit
test. All 22 pre-existing ratelimit tests were converted from `bool` to 
`int64_t`.
Not covered: the header itself in the response.

#### Upgrade notes

The header is additive and appears only on rejected requests.

Unlike `main`, the interval of the time to wait until the next request will be
accepted, is not configurable. It is fixed at 60s (`rgw_ratelimit_interval`). 
The config option has beenm added as part of dae572d, which is not part of this
backport.

**Upstream PRs:** https://github.com/ceph/ceph/pull/68210

## Bug fixes

### Fix Swift ACL evaluation for Glance image sharing

Fix Swift ACL evaluation with Keystone so Glance images stored in a multi-tenant Swift backend can be shared across projects. Without this fix, accepted shared images are visible to destination projects, but downloading them returns an empty file and fails checksum validation.

#### Related tickets

- cobaltcore-dev/cloud-storage#618
- cobaltcore-dev/cloud-storage#477

#### Behavior change

Authenticated Keystone users can now access containers granted through *:*. S3 requests authenticated through Keystone also honor Swift-style project:user and wildcard ACL entries. Bare role-name ACLs remain intentionally unsupported.

#### Risks

There is no runtime configuration toggle for this behavior. To disable it after rollout, roll back to the previous RGW package/build and restart or roll the RGW daemons. As an immediate mitigation, remove or restrict the affected Swift cross-project or wildcard ACL entries; a package rollback requires no data migration or ACL rewrite.
Authorization behavior is affected, but only for Keystone-authenticated RGW requests using Swift/S3 ACL interoperability. The backport is clean with no data structure change and includes focused unit coverage plus validation in a Swift/Glance environment.

#### Upgrade notes

No configuration, data migration, restart sequencing, or ACL rewrite is needed. Deploy the updated RGW packages and restart/roll the RGW daemons according to the normal upgrade procedure. Existing ACLs take effect automatically.

**Upstream PRs:** https://github.com/ceph/ceph/pull/68795, https://github.com/ceph/ceph/pull/70997

### Prevent rate limit credit going negative

Sensible bugfix. Especially in combination with https://github.com/ceph/ceph/pull/68210 .

#### Related tickets

- cobaltcore-dev/cloud-storage#621
- https://github.com/ceph/ceph/commit/91e9f00a7543c4651a983c2d785696a069d8ab28
- https://github.com/ceph/ceph/pull/66509
- cobaltcore-dev/cloud-storage/#585

#### Behavior change

The op counter can no longer go negative, so a user or bucket running with a
limit of 0 ("unlimited") no longer builds up hidden (negative) debt. Setting a
real limit later now takes effect immediately instead of refusing requests
until the debt is repaid. Together with the Retry-After backport, this also
bounds the Retry-After value, which is derived from the deficit.

#### Risks

**blast: availability**: the code runs on every request that rate limiting
applies to. But by the time it runs, the decision to accept or refuse the
request has already been made. Nothing changes for anyone who has a real limit
configured. The only case that behaves differently is a limit set to 0, meaning
unlimited. If this went wrong, the effect would be users getting through more
or fewer requests than their quota allows. That is recoverable and no data is
at risk, which is why it is availability rather than data-loss.

**conflict: trivial**: the patch did not apply cleanly. But the resolution was
trivial. Upstream is written on top of dae572d (LIST & DELETE rate limits),
which this release does not have. So the list and delete related parts were
dropped. What remains is the two read and write guards, plus the two matching
tests adapted to this branch's constructor, call signature and int64_t return.

**coverage: partial**: two unit tests added and adapted to this branch. One for
read, one for write. No integration-level test exercises the situation where
a gateway is enabled with 0 and gets later a limit assigned.

#### Upgrade notes

None. Counters live only in RGW process memory, so any accumulated debt is
discarded when the daemon restarts during the upgrade.

**Upstream PRs:** https://github.com/ceph/ceph/pull/66509

### upgrade nvmeof container image version to fix gateway startup

Since 19.2.6, cephadm creates daemon cephx keys with the `aes256k` key type.
The NVMe-oF gateway image shipped as the default, `quay.io/ceph/nvmeof:1.2.5`,
bundles a librados built from ceph 19.0.0, from before `aes256k` existed, so
the gateway cannot authenticate with the key cephadm gives it. It fails to
connect to the cluster and restarts, and the nvmeof service never reaches its
target count.

`quay.io/ceph/nvmeof:1.4.29` is built on ceph 19.2.7 and uses that key without
help, so the gateway works with the keys cephadm already creates.

#### Related tickets

- cobaltcore-dev/cloud-storage#625
- https://tracker.ceph.com/issues/81778

#### Behavior change

The default NVMe-oF gateway image moves from `quay.io/ceph/nvmeof:1.2.5` to
`quay.io/ceph/nvmeof:1.4.29`, in the mgr module, in the cephadm binary
constants (which still named 1.2.1) and in the example listing in the
monitoring docs. Clusters that pin `mgr/cephadm/container_image_nvmeof` keep
their pinned image. If that image predates `aes256k` they stay broken until
they move the pin.

#### Risks

- **blast: availability**: the change is the value of `DEFAULT_NVMEOF_IMAGE`
  plus the revert of the previous backport, which removes cephadm's
  nvmeof-specific key handling and leaves those files identical to upstream
  squid. A wrong image means gateways do not start, which is the failure this
  fixes. No data path is touched and no on-disk format changes, so nothing can
  be silently corrupted. Clusters with no nvmeof service are unaffected.
- **conflict: substantive**: fully custom downstream change, not a cherry-pick,
  so it carries no upstream review (rubric: "... OR fully custom"). The diff is
  the revert of the previous backport plus three constants and a template
  comment, and will carry forward mechanically until upstream squid bumps its
  own default.
- **coverage: partial**: integration coverage only, no unit test for an image
  constant. `smoke-roleless` exercises gateway startup with the shipped image
  on centos and ubuntu. Not covered: end-to-end I/O on the shipped image,
  because `qa/suites/rbd/nvmeof` pins `version: latest` and therefore tests a
  main-line gateway rather than this one.
- 1.2.5 to 1.4.29 is a two-minor-version jump in the gateway itself, not only
  a librados rebuild, so gateway behaviour beyond startup rests on upstream's
  testing of the 1.4 line. Checked ahead of the jump: the rendered
  `ceph-nvmeof.conf` keeps the same six sections and every setting 1.4.29 reads
  without a default is emitted by the template. The gRPC surface is additive
  (25 RPCs to 32, none removed). And the container surface squid's cephadm
  provides is what 1.4.x expects, with every addition in tentacle's version
  gated on config-json keys squid never sets. Under 1.4.x the presence of
  `bdevs_per_cluster` in the gateway config is what selects how the gateway
  groups its RADOS connections, not just how many, so the line can no longer
  be removed as a redundant tunable. The template now carries a comment saying
  so.

#### Upgrade notes

Clusters without an NVMe-oF service: nothing to do.

An nvmeof service already stuck from a 19.2.6 or later deploy does not pick up
the new image on its own. Redeploy it once after the upgrade:

```
ceph orch redeploy nvmeof.<service>
```

The gateway is recreated from 1.4.29 and starts with the key it already has.
No cephx surgery is needed.


## Integration and build patches

### Release bootstrap

bootstrap files used by release-management tool

#### Related tickets

- cobaltcore-dev/cloud-storage#607
- none

#### Behavior change

None. Build-only change: the `chown` of `node-env/src` is skipped when
nodeenv (>= 1.11.0) did not leave that directory behind; with older
nodeenv versions the build behaves as before. The produced binaries and
dashboard assets are unchanged.

#### Risks

- **blast: availability** — the change touches only the build of the
  dashboard frontend (`src/pybind/mgr/dashboard/frontend/CMakeLists.txt`).
  Without it, every build with `WITH_MGR_DASHBOARD_FRONTEND` fails at the
  "dashboard nodeenv is being installed" step since nodeenv 1.11.0, so no
  packages or images can be produced. No runtime code is changed.
- **conflict: clean** — cherry-picked from the squid backport
  (ceph/ceph#72167, c96865f0e89e); the resulting diff is identical to the
  upstream squid commit. The squid-vs-main conflict was already resolved
  upstream.
- **coverage: weak** — no unit test covers the CMake rule. It is exercised
  by any build with the dashboard frontend enabled (e.g. the unit test CI
  workflow), which fails without this fix.

#### Upgrade notes

None.

**Upstream PRs:** https://github.com/ceph/ceph/pull/72108, https://github.com/ceph/ceph/pull/72167

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

## Active patches

Cumulative; one row per backport carried in this release.

| Component | Title | Category | Risk |
|---|---|---|---|
| build | Release bootstrap | integration | medium (7) |
| other | upgrade nvmeof container image version to fix gateway startup | fix | high (10) |
| rgw | IAM / Bucket Policy: Keystone role and user ID support | feature | low (5) |
| rgw | Write Lock Lua Extensions | feature | low (5) |
| rgw | Keystone Project RO/Viewer role + Implicit Deny | feature | medium (7) |
| rgw | KMS Cache | feature | medium (9) |
| rgw | Fix Swift ACL evaluation for Glance image sharing | fix | medium (9) |
| rgw | Add Keystone scope information to ops logging -> audit logs | feature | medium (7) |
| rgw | rate limit "retry after" header | feature | medium (8) |
| rgw | Prevent rate limit credit going negative | fix | medium (7) |
