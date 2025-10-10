// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:t -*-
// vim: ts=8 sw=2 smarttab ft=cpp
#pragma once

#include <string>
#include <vector>
#include <optional>

// Forward declarations to avoid heavy includes in header.
namespace rgw::keystone {
  class TokenEnvelope;
}
namespace ceph::common {
  class CephContext;
}

namespace rgw::auth {

/**
 * Minimal representation of Keystone authentication scope for ops logging.
 *
 * Design:
 *  - Owned strings for clear lifetimes.
 *  - Minimal data: only what ops logging needs.
 *  - Privacy-aware: IDs always present; names can be redacted by config.
 *
 * Emission policy:
 *  - Names are included only if cct->_conf->rgw_keystone_scope_include_user is true.
 *  - Roles are included only if cct->_conf->rgw_keystone_scope_include_roles is true.
 */
struct KeystoneScope {
  struct Domain {
    std::string id;
    std::string name; // empty if redacted

    Domain() = default;
    Domain(std::string id_, std::string name_)
      : id(std::move(id_)), name(std::move(name_)) {}
  };

  struct Project {
    std::string id;
    std::string name; // empty if redacted
    Domain domain;
  };

  struct User {
    std::string id;
    std::string name; // empty if redacted
    Domain domain;
  };

  struct ApplicationCredential {
    std::string id;
    std::string name; // empty if redacted
    bool restricted{false};
  };

  Project project;
  User user;
  std::vector<std::string> roles;                       // role names only; may be empty
  std::optional<ApplicationCredential> app_cred;        // present if token carried app-cred

  /**
   * Extract a privacy-aware scope from a validated Keystone token.
   *
   * @param token  Validated Keystone token envelope.
   * @param cct    CephContext (may be nullptr). If null, defaults to IDs-only and roles included.
   * @return       A KeystoneScope with owned strings, safe to log.
   */
  [[nodiscard]]
  static KeystoneScope from_token(const rgw::keystone::TokenEnvelope& token,
                                  ceph::common::CephContext* cct);
};

} // namespace rgw::auth