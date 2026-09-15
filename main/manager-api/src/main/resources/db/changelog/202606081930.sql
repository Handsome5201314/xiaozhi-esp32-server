-- Add optional RAGFlow pipeline dataset fields without changing existing records.
SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'parse_type');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `parse_type` int DEFAULT NULL COMMENT ''RAGFlow pipeline parse type''', 'SELECT ''Column parse_type already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @col_exists = (SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ai_rag_dataset' AND COLUMN_NAME = 'pipeline_id');
SET @sql = IF(@col_exists = 0, 'ALTER TABLE `ai_rag_dataset` ADD COLUMN `pipeline_id` varchar(32) DEFAULT NULL COMMENT ''RAGFlow pipeline ID''', 'SELECT ''Column pipeline_id already exists'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
