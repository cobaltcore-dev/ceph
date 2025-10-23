// -*- mode:C++; tab-width:8; c-basic-offset:2; indent-tabs-mode:t -*-
// vim: ts=8 sw=2 smarttab ft=cpp

#pragma once

#include <optional>
#include <string>
#include <vector>

#include "include/buffer.h"
#include "include/encoding.h"

class CephContext;

namespace ceph {
  class Formatter;
}

namespace rgw::keystone {

// Forward declaration
class TokenEnvelope;

/**
 * Keystone authentication scope information.
 *
 * This structure captures the OpenStack Keystone authentication context
 * including project, user, roles, and application credentials. It's used
 * throughout the authentication and logging pipeline.
 *
 * The structure supports:
 * - Binary encoding/decoding for RADOS backend (ops log storage)
 * - JSON formatting for file/socket backend (ops log output)
 * - Granular control via configuration flags (include_user, include_roles)
 */
struct ScopeInfo {
  /**
   * Keystone domain information.
   * Domains provide namespace isolation in Keystone.
   */
  struct domain_t {
    std::string id;
    std::string name;

    void encode(bufferlist &bl) const {
      ENCODE_START(1, 1, bl);
      encode(id, bl);
      encode(name, bl);
      ENCODE_FINISH(bl);
    }
    void decode(bufferlist::const_iterator &p) {
      DECODE_START(1, p);
      decode(id, p);
      decode(name, p);
      DECODE_FINISH(p);
    }
  };

  /**
   * Keystone project (tenant) information.
   * Projects are the primary authorization scope in Keystone.
   */
  struct project_t {
    std::string id;
    std::string name;
    domain_t domain;

    void encode(bufferlist &bl) const {
      ENCODE_START(1, 1, bl);
      encode(id, bl);
      encode(name, bl);
      domain.encode(bl);
      ENCODE_FINISH(bl);
    }
    void decode(bufferlist::const_iterator &p) {
      DECODE_START(1, p);
      decode(id, p);
      decode(name, p);
      domain.decode(p);
      DECODE_FINISH(p);
    }
  };

  /**
   * Keystone user information.
   * Optional based on rgw_keystone_scope_include_user configuration.
   */
  struct user_t {
    std::string id;
    std::string name;
    domain_t domain;

    void encode(bufferlist &bl) const {
      ENCODE_START(1, 1, bl);
      encode(id, bl);
      encode(name, bl);
      domain.encode(bl);
      ENCODE_FINISH(bl);
    }
    void decode(bufferlist::const_iterator &p) {
      DECODE_START(1, p);
      decode(id, p);
      decode(name, p);
      domain.decode(p);
      DECODE_FINISH(p);
    }
  };

  /**
   * Keystone application credential information.
   * Only present when authentication used application credentials.
   */
  struct app_cred_t {
    std::string id;
    std::string name;
    bool restricted;

    void encode(bufferlist &bl) const {
      ENCODE_START(1, 1, bl);
      encode(id, bl);
      encode(name, bl);
      encode(restricted, bl);
      ENCODE_FINISH(bl);
    }
    void decode(bufferlist::const_iterator &p) {
      DECODE_START(1, p);
      decode(id, p);
      decode(name, p);
      decode(restricted, p);
      DECODE_FINISH(p);
    }
  };

  // Fields
  project_t project;                        // Always present
  std::optional<user_t> user;               // Optional (controlled by include_user config)
  std::vector<std::string> roles;           // May be empty (controlled by include_roles config)
  std::optional<app_cred_t> app_cred;       // Optional (present only for app cred auth)

  // Serialization for RADOS backend
  void encode(bufferlist &bl) const {
    ENCODE_START(1, 1, bl);
    project.encode(bl);

    __u8 has_user = user.has_value();
    encode(has_user, bl);
    if (has_user) {
      user->encode(bl);
    }

    encode(roles, bl);

    __u8 has_app_cred = app_cred.has_value();
    encode(has_app_cred, bl);
    if (has_app_cred) {
      app_cred->encode(bl);
    }
    ENCODE_FINISH(bl);
  }

  void decode(bufferlist::const_iterator &p) {
    DECODE_START(1, p);
    project.decode(p);

    __u8 has_user;
    decode(has_user, p);
    if (has_user) {
      user = user_t{};
      user->decode(p);
    } else {
      user = std::nullopt;
    }

    decode(roles, p);

    __u8 has_app_cred;
    decode(has_app_cred, p);
    if (has_app_cred) {
      app_cred = app_cred_t{};
      app_cred->decode(p);
    } else {
      app_cred = std::nullopt;
    }
    DECODE_FINISH(p);
  }

  // JSON formatting for file/socket backend
  void dump(ceph::Formatter *f) const;
};

/**
 * Build ScopeInfo from Keystone token and configuration.
 *
 * This helper function eliminates code duplication between TokenEngine
 * and EC2Engine by centralizing the scope building logic.
 *
 * @param cct CephContext for configuration access
 * @param token TokenEnvelope containing Keystone authentication data
 * @return ScopeInfo if scope logging enabled, nullopt otherwise
 */
std::optional<ScopeInfo> build_scope_info(
    CephContext* cct,
    const TokenEnvelope& token);

} // namespace rgw::keystone
