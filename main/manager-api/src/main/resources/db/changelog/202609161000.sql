ALTER TABLE `ai_hermes_instance`
    ADD COLUMN `tool_permissions_json` JSON NULL AFTER `capabilities_json`,
    ADD COLUMN `summary_receive_enabled` TINYINT NOT NULL DEFAULT 1 AFTER `is_healthy`,
    ADD COLUMN `last_summary_at` DATETIME NULL AFTER `last_health_at`,
    ADD COLUMN `last_summary_error` VARCHAR(512) NULL AFTER `last_summary_at`;
