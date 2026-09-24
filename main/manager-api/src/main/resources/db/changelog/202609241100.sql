-- Backfill the personal tenant scope for users created before registration
-- started provisioning ai_tenant_member. Existing active memberships win, so
-- this migration cannot move a user out of an explicitly assigned tenant.
INSERT INTO `ai_tenant` (`name`, `status`, `plan_code`)
SELECT CONCAT('user-', u.`id`), 'ACTIVE', 'default'
FROM `sys_user` u
LEFT JOIN `ai_tenant_member` m
  ON m.`user_id` = u.`id` AND m.`status` = 'ACTIVE'
WHERE m.`user_id` IS NULL
ON DUPLICATE KEY UPDATE `name` = VALUES(`name`);

INSERT INTO `ai_tenant_member` (`tenant_id`, `user_id`, `role_code`, `status`)
SELECT t.`id`, u.`id`, 'member', 'ACTIVE'
FROM `sys_user` u
JOIN `ai_tenant` t ON t.`name` = CONCAT('user-', u.`id`)
LEFT JOIN `ai_tenant_member` m
  ON m.`user_id` = u.`id` AND m.`status` = 'ACTIVE'
WHERE m.`user_id` IS NULL
ON DUPLICATE KEY UPDATE `status` = VALUES(`status`);

-- Existing devices inherit the deterministic active tenant of their owner.
-- The MIN() choice is stable for legacy users that already have memberships.
UPDATE `ai_device` d
JOIN (
    SELECT `user_id`, MIN(`tenant_id`) AS `tenant_id`
    FROM `ai_tenant_member`
    WHERE `status` = 'ACTIVE'
    GROUP BY `user_id`
) m ON m.`user_id` = d.`user_id`
SET d.`tenant_id` = m.`tenant_id`
WHERE d.`tenant_id` IS NULL;
