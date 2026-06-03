-- Register AI scale assessment as a selectable server plugin in the manager console.
-- Chinese text is built from UTF-8 bytes to avoid mojibake when SQL files pass through
-- different shells or database clients during Docker/Liquibase startup.
SET NAMES utf8mb4;
SET @ai_scale_name = CONVERT(UNHEX('4149E9878FE8A1A8E8AF84E4BCB0') USING utf8mb4);
SET @ai_scale_label_base_url = CONVERT(UNHEX('E9878FE8A1A8E69C8DE58AA1E59CB0E59D80') USING utf8mb4);
SET @ai_scale_label_prefix = CONVERT(UNHEX('E8AEBEE5A4874944E5898DE7BC80') USING utf8mb4);
SET @ai_scale_label_nickname = CONVERT(UNHEX('E9BB98E8AEA4E68890E59198E698B5E7A7B0') USING utf8mb4);
SET @ai_scale_label_description = CONVERT(UNHEX('E5B7A5E585B7E68F8FE8BFB0') USING utf8mb4);
SET @ai_scale_default_nickname = CONVERT(UNHEX('E69CACE4BABA') USING utf8mb4);
SET @ai_scale_description = CONVERT(UNHEX('E5BD93E794A8E688B7E683B3E5819AE68385E7BBAAE38081E784A6E89991E38081E6B3A8E6848FE58A9BE38081E58F91E882B2E38081E79DA1E79CA0E38081E8A18CE4B8BAE79BB8E585B3E7AD9BE69FA5E697B6E8B083E794A8E38082E4B88DE8A681E887AAE8A18CE7BC96E980A0E9878FE8A1A8E9A298E79BAEE38081E58886E695B0E68896E58CBBE5ADA6E8AF8AE696ADE38082') USING utf8mb4);
SET @ai_scale_fields = JSON_ARRAY(
    JSON_OBJECT('key', 'base_url', 'type', 'string', 'label', @ai_scale_label_base_url, 'default', 'https://tongyimohe.cloud', 'editing', false, 'selected', false),
    JSON_OBJECT('key', 'partner_token', 'type', 'string', 'label', 'Partner Token', 'default', '', 'editing', false, 'selected', false),
    JSON_OBJECT('key', 'device_id_prefix', 'type', 'string', 'label', @ai_scale_label_prefix, 'default', 'xiaozhi', 'editing', false, 'selected', false),
    JSON_OBJECT('key', 'default_nickname', 'type', 'string', 'label', @ai_scale_label_nickname, 'default', @ai_scale_default_nickname, 'editing', false, 'selected', false),
    JSON_OBJECT('key', 'description', 'type', 'string', 'label', @ai_scale_label_description, 'default', @ai_scale_description, 'editing', false, 'selected', false)
);

INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`)
VALUES ('SYSTEM_PLUGIN_AI_SCALE', 'Plugin', 'ai_scale_assessment', @ai_scale_name, @ai_scale_fields, 90, 0, NOW(), 0, NOW())
ON DUPLICATE KEY UPDATE
    `provider_code` = VALUES(`provider_code`),
    `name` = VALUES(`name`),
    `fields` = VALUES(`fields`),
    `sort` = VALUES(`sort`),
    `updater` = VALUES(`updater`),
    `update_date` = VALUES(`update_date`);
