---
id: 01a134b3-2aac-7c51-bf7f-dcb3cb6babbc
title: Prevent rate limit credit going negative
component: rgw
category: fix
provenance:
  type: upstream_pr
  upstream_prs:
  - https://github.com/ceph/ceph/pull/66509
  upstream_pr_state: merged-main
  upstream_commits:
  - 91e9f00a7543c4651a983c2d785696a069d8ab28
  upstream_trackers:
  - https://tracker.ceph.com/issues/74088
justification:
  type: engineering
  refs:
  - cobaltcore-dev/cloud-storage#602
  - todo
  - '```'
  - https://github.com/ceph/ceph/commit/91e9f00a7543c4651a983c2d785696a069d8ab28
  - '- https://github.com/ceph/ceph/pull/66509'
  - cobaltcore-dev/cloud-storage/#585
risk:
  # Stage-B — fill these during PR prep. See release-management/backports/RISK-RUBRIC.md.
  blast: availability
  conflict: trivial
  coverage: partial
---

## Justification (public)

Sensible bugfix. Especially in combination with https://github.com/ceph/ceph/pull/68210 .

## Justification (internal)

With the rate limiter enabled and `max_write_ops = 0` ("unlimited"), every request still decrements the token counter and nothing refills a zero-limit bucket. So it drifts negative without bound. Nothing misbehaves until an
operator later sets a real limit, at which point all that debt must be repaid before a single request is admitted.

Because of the https://github.com/cobaltcore-dev/cloud-storage/issues/585 backport the bugfix becomes more important. Before: without the retry-header, if a client was rejected, he could have re-tried it immediately. But afterwards: If the header exist and the client honors it, the client will wait for 14h, if he is told to do so.

## Risk notes

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

## Behavior change

The op counter can no longer go negative, so a user or bucket running with a
limit of 0 ("unlimited") no longer builds up hidden (negative) debt. Setting a
real limit later now takes effect immediately instead of refusing requests
until the debt is repaid. Together with the Retry-After backport, this also
bounds the Retry-After value, which is derived from the deficit.

## Upgrade notes

None. Counters live only in RGW process memory, so any accumulated debt is
discarded when the daemon restarts during the upgrade.
