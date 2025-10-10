// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:t -*-
// vim: ts=8 sw=2 smarttab ft=cpp

#include "rgw_auth_keystone_decorating_applier.h"
#include "rgw_auth_keystone_scope.h"
#include "common/dout.h"

#define dout_subsys ceph_subsys_rgw

namespace rgw::auth::keystone {

void KeystoneDecoratingApplier::write_ops_log_entry(rgw_log_entry& entry) const {
  // Call inner applier first
  if (inner) {
    inner->write_ops_log_entry(entry);
  }

  // Global ops-log gate
  if (!cct || !cct->_conf->rgw_enable_ops_log) {
    return;
  }

  // Feature gate
  if (!cct->_conf->rgw_keystone_scope_enabled) {
    return;
  }

  // Build minimal scope from token (privacy flags applied inside from_token)
  auto scope = KeystoneScope::from_token(token, cct);

  // Emplace directly into entry to avoid an extra temporary
  entry.keystone_scope.emplace();
  auto& ks = *entry.keystone_scope;

  // Project
  ks.project.id             = std::move(scope.project.id);
  ks.project.name           = std::move(scope.project.name);        // may be empty if privacy mode
  ks.project.domain.id      = std::move(scope.project.domain.id);
  ks.project.domain.name    = std::move(scope.project.domain.name); // may be empty

  // User
  ks.user.id                = std::move(scope.user.id);
  ks.user.name              = std::move(scope.user.name);           // may be empty
  ks.user.domain.id         = std::move(scope.user.domain.id);
  ks.user.domain.name       = std::move(scope.user.domain.name);    // may be empty

  // Roles
  ks.roles                  = std::move(scope.roles);

  // Application credential (if Patch 3 is in tree)
  if (scope.app_cred) {
    rgw_log_entry::keystone_scope_t::app_cred_t ac;
    ac.id          = std::move(scope.app_cred->id);
    ac.name        = std::move(scope.app_cred->name);       // may be empty
    ac.restricted  = scope.app_cred->restricted;
    ks.app_cred    = std::move(ac);
  }

  ldout(cct, 20) << "Injected Keystone scope into ops log entry" << dendl;
}

} // namespace rgw::auth::keystone