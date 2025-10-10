// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:t -*-
// vim: ts=8 sw=2 smarttab ft=cpp
#pragma once

#include "rgw_auth.h"                 // IdentityApplier, ACLOwner, etc.
#include "rgw_keystone.h"             // rgw::keystone::TokenEnvelope
#include "rgw_auth_keystone_scope.h"  // rgw::auth::KeystoneScope
#include "rgw_log.h"                  // rgw_log_entry

namespace rgw::auth::keystone {

/**
 * Decorator that wraps an IdentityApplier and augments ops log with Keystone scope.
 *
 * Design:
 * - Forwards all IdentityApplier methods to the wrapped 'inner' applier.
 * - Owns the validated Keystone TokenEnvelope (moved in ctor).
 * - Injects 'keystone_scope' into ops log via write_ops_log_entry().
 * - Does NOT modify req_state (log-only behavior).
 */
class KeystoneDecoratingApplier final : public IdentityApplier {
  CephContext* cct;                           // not owned
  IdentityApplier::aplptr_t inner;            // wrapped applier (factory-created)
  rgw::keystone::TokenEnvelope token;         // owned copy (moved from engine)

public:
  KeystoneDecoratingApplier(CephContext* cct_,
                            IdentityApplier::aplptr_t inner_,
                            rgw::keystone::TokenEnvelope&& token_)
    : cct(cct_),
      inner(std::move(inner_)),
      token(std::move(token_)) {}

  ~KeystoneDecoratingApplier() override = default;

  // --------- Transparent forwarding (keep behavior identical to inner) ---------

  void modify_request_state(const DoutPrefixProvider* dpp,
                            req_state* s) const override {
    if (inner) inner->modify_request_state(dpp, s);
  }

  ACLOwner get_aclowner() const override {
    return inner ? inner->get_aclowner() : ACLOwner{};
  }

  uint32_t get_perms_from_aclspec(const DoutPrefixProvider* dpp,
                                  const aclspec_t& aclspec) const override {
    return inner ? inner->get_perms_from_aclspec(dpp, aclspec) : 0;
  }

  bool is_admin_of(const rgw_owner& o) const override {
    return inner && inner->is_admin_of(o);
  }

  bool is_owner_of(const rgw_owner& o) const override {
    return inner && inner->is_owner_of(o);
  }

  uint32_t get_perm_mask() const override {
    return inner ? inner->get_perm_mask() : 0;
  }

  void to_str(std::ostream& out) const override {
    if (inner) inner->to_str(out);
  }

  bool is_identity(const Principal& p) const override {
    return inner && inner->is_identity(p);
  }

  uint32_t get_identity_type() const override {
    return inner ? inner->get_identity_type() : TYPE_NONE;
  }

  std::string get_acct_name() const override {
    return inner ? inner->get_acct_name() : std::string{};
  }

  std::string get_subuser() const override {
    return inner ? inner->get_subuser() : std::string{};
  }

  // NOTE: These two return references; provide safe statics when inner is null.
  const std::string& get_tenant() const override {
    static const std::string empty;
    return inner ? inner->get_tenant() : empty;
  }

  const std::optional<RGWAccountInfo>& get_account() const override {
    static const std::optional<RGWAccountInfo> empty;
    return inner ? inner->get_account() : empty;
  }

  void load_acct_info(const DoutPrefixProvider* dpp, RGWUserInfo& user_info) const override {
    if (inner) {
      inner->load_acct_info(dpp, user_info);
    }
  }

  // ----------------------------- Augmentation -----------------------------

  /**
   * Augment ops log with Keystone scope.
   * Calls inner applier first, then (if enabled) injects 'keystone_scope'.
   */
  void write_ops_log_entry(rgw_log_entry& entry) const override;
};

} // namespace rgw::auth::keystone