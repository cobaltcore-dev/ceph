# cobaltcore-storage 19.2.4-fasttrack-1

**Upstream base:** 19.2.4 (v19.2.4)
**Downstream tag:** release/cobaltcore-storage-v19.2.4-fasttrack-1
**Branch:** squid-19.2.4-cobaltcore-storage

## Built artifacts

- **container-image**: `harbor.clyso.com/custom-ceph/ceph/ceph:cobaltcore-storage-v19.2.4-fasttrack-1` (`sha256:362537d9d98c78d79e8afeee1481c9607b37c8e229a55abb840abf691e49f885`)- **container-image**: `ghcr.io/cobaltcore-dev/ceph:cobaltcore-storage-v19.2.4-fasttrack-1` (`sha256:362537d9d98c78d79e8afeee1481c9607b37c8e229a55abb840abf691e49f885`)
## Verification

See `release-management/releases/v19.2.4-fasttrack-1/RELEASE.md` for the authoritative build and
test record (source commit, artifact digests, RE identity, full test
summary) and `release-management/releases/v19.2.4-fasttrack-1/test-evidence/` for raw
test artifacts.

## New features

### KMS Cache

Adds a secure in-memory cache for SSE-KMS encryption keys retrieved from Barbican (or other KMS backends), eliminating redundant round-trips on repeated access to the same encrypted objects. Uses a new SIEVE-based eviction cache (WebCache) and stores decrypted secrets in the Linux kernel keyring.
Please refer to the Ceph documentation on how to configure this feature.

#### Related tickets

- cobaltcore-dev/cloud-storage#463
- https://github.com/cobaltcore-dev/cloud-storage/issues/125

#### Behavior change

Repeated SSE-KMS access no longer hits the KMS backend on every
request; decrypted secrets are cached in-memory and in the Linux
kernel keyring. KMS-cache is ON out of the box.

#### Risks

- TTLs mean that a deleted or rotated Barbican key won't be immediately reflected.
- New async primitives (async::call_once) and the WebCache are significant new library code shipping for the first time.
- Cache size tuning and system wide keyring quota adjustment needed for production workloads (refer to the docs).

#### Upgrade notes

Feature flag: rgw_crypt_s3_kms_cache_enabled. Set false to disable caching entirely and revert to per-request KMS lookups.

**Upstream PRs:** https://github.com/ceph/ceph/pull/61256

### Add Keystone scope information to ops logging

Add OpenStack Keystone authentication scope information to RGW operations logs.

It enables audit trails for multi-tenant and compliance-sensitive
environments, by adding the keystone_scope field (project, user,
domain, roles, application credentials) to RGW ops logs.

#### Related tickets

- cobaltcore-dev/cloud-storage#464
- https://github.com/cobaltcore-dev/cloud-storage/issues/335

#### Behavior change

Keystone scope (project, domain, roles) appears in RGW ops logs. This feature is OFF by default.

#### Risks

Scope logging with `rgw_keystone_scope_include_user=true` writes human-readable usernames to ops logs, which may have GDPR / privacy implications.

#### Upgrade notes

- `rgw_keystone_scope_enabled` - enable Keystone scope in the ops log

**Upstream PRs:** https://github.com/ceph/ceph/pull/66111

### Write Lock Lua Extensions

RGW Lua scripting extensions to allow "Write Lock" feature

- New postAuth Lua hook point that runs after authentication / authorization but before the operation executes.
- Lua scripts can now read bucket tags.
- Lua scripts can abort request processing.

#### Related tickets

- cobaltcore-dev/cloud-storage#465
- https://github.com/cobaltcore-dev/cloud-storage/issues/310

#### Behavior change

A new postAuth Lua hook point is available. Scripts can read bucket
tags and abort request processing. Lua is inactive out of the box (no
scripts are uploaded by default).

#### Risks

The postAuth hook runs on every request. A slow or buggy Lua script will add latency to all S3 operations.

#### Upgrade notes

No dedicated feature flag; controlled by whether a Lua script is uploaded via radosgw-admin.

**Upstream PRs:** https://github.com/ceph/ceph/pull/67219, https://github.com/ceph/ceph/pull/67548, https://github.com/ceph/ceph/pull/66065

## Active patches

Cumulative; one row per backport carried in this release.

| Component | Title | Category | Risk |
|---|---|---|---|
| rgw | KMS Cache | feature | medium (9) |
| rgw | Add Keystone scope information to ops logging | feature | medium (7) |
| rgw | Write Lock Lua Extensions | feature | medium (7) |
