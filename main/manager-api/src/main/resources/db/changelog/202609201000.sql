ALTER TABLE `ai_hermes_instance`
    ADD COLUMN `model` VARCHAR(128) NOT NULL DEFAULT '' AFTER `base_url`,
    MODIFY COLUMN `user_id` BIGINT NULL;
