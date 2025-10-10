// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:t -*-
// vim: ts=8 sw=2 smarttab ft=cpp

#include "rgw_auth_keystone_scope.h"
#include "rgw_keystone.h"
#include "common/ceph_context.h"
#include "common/dout.h"

#define dout_subsys ceph_subsys_rgw

using namespace ceph::common;

namespace rgw::auth {

KeystoneScope KeystoneScope::from_token(
  const rgw::keystone::TokenEnvelope& token,
  ceph::common::CephContext* cct)
{
  KeystoneScope scope;

  // Config flags
  const bool include_names = (cct && cct->_conf->rgw_keystone_scope_include_user);
  const bool include_roles = (cct && cct->_conf->rgw_keystone_scope_include_roles);

  // ---- Project ----
  scope.project.id = token.project.id;
  scope.project.name = include_names ? token.project.name : "";
  scope.project.domain.id = token.project.domain.id;
  scope.project.domain.name = include_names ? token.project.domain.name : "";

  // ---- User ----
  scope.user.id = token.user.id;
  scope.user.name = include_names ? token.user.name : "";
  scope.user.domain.id = token.user.domain.id;
  scope.user.domain.name = include_names ? token.user.domain.name : "";

  // ---- Roles ----
  if (include_roles && !token.roles.empty()) {
    scope.roles.reserve(token.roles.size());
    for (const auto& role : token.roles) {
      scope.roles.push_back(role.name); // copy role name only
    }
  }

  // ---- Application credential (optional) ----
  // If TokenEnvelope has app_cred as std::optional<>
  if (token.app_cred.has_value()) {
    ApplicationCredential ac;
    ac.id = token.app_cred->id;
    ac.name = include_names ? token.app_cred->name : "";
    ac.restricted = token.app_cred->restricted;
    scope.app_cred = std::move(ac);
  }

  // Debug log (level 20 = deep debug)
  if (cct) {
    ldout(cct, 20) << "KeystoneScope extracted: project_id=" << scope.project.id
                   << " user_id=" << scope.user.id
                   << " roles=" << scope.roles.size()
                   << " app_cred=" << (scope.app_cred ? "yes" : "no")
                   << dendl;
  }

  return scope;
}

} // namespace rgw::auth