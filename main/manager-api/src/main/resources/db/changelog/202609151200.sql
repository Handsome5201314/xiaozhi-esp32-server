-- Unified tenant boundary. Third party secrets are encrypted by the application
-- and are never stored in provider_profile.config_json.
CREATE TABLE IF NOT EXISTS `ai_tenant` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(128) NOT NULL,
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `plan_code` VARCHAR(64) NOT NULL DEFAULT 'default',
    `policy_json` JSON NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`), UNIQUE KEY `uk_ai_tenant_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `ai_tenant_member` (
    `tenant_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    `role_code` VARCHAR(32) NOT NULL DEFAULT 'member',
    `status` VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`tenant_id`, `user_id`), KEY `idx_member_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

ALTER TABLE `ai_device` ADD COLUMN `tenant_id` BIGINT NULL AFTER `user_id`;
CREATE INDEX `idx_ai_device_tenant_user` ON `ai_device` (`tenant_id`, `user_id`);

CREATE TABLE IF NOT EXISTS `ai_provider_profile` (
    `id` VARCHAR(36) NOT NULL,
    `tenant_id` BIGINT NOT NULL,
    `user_id` BIGINT NULL,
    `device_id` VARCHAR(36) NULL,
    `capability` VARCHAR(16) NOT NULL,
    `provider_type` VARCHAR(64) NOT NULL,
    `display_name` VARCHAR(128) NOT NULL,
    `base_url` VARCHAR(512) NOT NULL,
    `model_name` VARCHAR(128) NULL,
    `secret_ref` VARCHAR(128) NULL,
    `priority` INT NOT NULL DEFAULT 100,
    `is_enabled` TINYINT NOT NULL DEFAULT 1,
    `is_healthy` TINYINT NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`), KEY `idx_provider_route` (`tenant_id`, `user_id`, `device_id`, `capability`, `is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `ai_provider_secret` (
    `id` VARCHAR(36) NOT NULL,
    `tenant_id` BIGINT NOT NULL,
    `owner_user_id` BIGINT NULL,
    `secret_ref` VARCHAR(128) NOT NULL,
    `ciphertext` MEDIUMTEXT NOT NULL,
    `key_version` VARCHAR(32) NOT NULL DEFAULT 'v1',
    `masked_value` VARCHAR(32) NOT NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`), UNIQUE KEY `uk_secret_ref` (`secret_ref`), KEY `idx_secret_owner` (`tenant_id`, `owner_user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `ai_hermes_instance` (
    `id` VARCHAR(36) NOT NULL,
    `tenant_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    `device_id` VARCHAR(36) NULL,
    `name` VARCHAR(128) NOT NULL,
    `base_url` VARCHAR(512) NOT NULL,
    `secret_ref` VARCHAR(128) NULL,
    `capabilities_json` JSON NOT NULL,
    `priority` INT NOT NULL DEFAULT 100,
    `is_enabled` TINYINT NOT NULL DEFAULT 1,
    `is_healthy` TINYINT NOT NULL DEFAULT 1,
    `last_health_at` DATETIME NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`), KEY `idx_hermes_route` (`tenant_id`, `user_id`, `device_id`, `is_enabled`, `priority`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `ai_checklist_binding` (
    `id` VARCHAR(36) NOT NULL,
    `tenant_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    `device_id` VARCHAR(36) NULL,
    `provider_type` VARCHAR(32) NOT NULL DEFAULT 'feishu',
    `secret_ref` VARCHAR(128) NOT NULL,
    `tasklist_ref` VARCHAR(128) NOT NULL,
    `assignee_ref` VARCHAR(128) NOT NULL,
    `permissions_json` JSON NOT NULL,
    `is_enabled` TINYINT NOT NULL DEFAULT 1,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`), KEY `idx_checklist_route` (`tenant_id`, `user_id`, `device_id`, `is_enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `ai_tenant_policy` (
    `tenant_id` BIGINT NOT NULL,
    `allowed_provider_types_json` JSON NOT NULL,
    `allowed_hosts_json` JSON NOT NULL,
    `max_concurrency` INT NOT NULL DEFAULT 4,
    `monthly_quota` BIGINT NULL,
    `allow_user_provider` TINYINT NOT NULL DEFAULT 1,
    `allow_legacy_checklist` TINYINT NOT NULL DEFAULT 1,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`tenant_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS `ai_audit_event` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `request_id` VARCHAR(64) NOT NULL,
    `tenant_id` BIGINT NULL,
    `user_id` BIGINT NULL,
    `device_id` VARCHAR(36) NULL,
    `event_type` VARCHAR(64) NOT NULL,
    `result_code` VARCHAR(32) NOT NULL,
    `metadata_json` JSON NULL,
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`), KEY `idx_audit_tenant_time` (`tenant_id`, `created_at`), KEY `idx_audit_request` (`request_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
