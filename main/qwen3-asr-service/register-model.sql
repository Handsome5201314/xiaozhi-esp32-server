INSERT INTO `ai_model_config` (
    `id`,
    `model_type`,
    `model_code`,
    `model_name`,
    `is_default`,
    `is_enabled`,
    `config_json`,
    `doc_link`,
    `remark`,
    `sort`,
    `creator`,
    `create_date`,
    `updater`,
    `update_date`
) VALUES (
    'ASR_Qwen3ASRLocal',
    'ASR',
    'Qwen3ASRLocal',
    'Qwen3-ASR-1.7B 本地识别',
    0,
    1,
    JSON_OBJECT(
        'type', 'openai',
        'api_key', 'local-only',
        'base_url', 'http://qwen3-asr:8000/v1/audio/transcriptions',
        'model_name', 'Qwen/Qwen3-ASR-1.7B',
        'output_dir', 'tmp/'
    ),
    'https://github.com/QwenLM/Qwen3-ASR',
    '运行于本机 RTX 3090 的 Qwen3-ASR-1.7B；服务仅通过 Docker 内部网络访问。',
    15,
    1,
    NOW(),
    1,
    NOW()
)
ON DUPLICATE KEY UPDATE
    `model_code` = VALUES(`model_code`),
    `model_name` = VALUES(`model_name`),
    `is_enabled` = 1,
    `config_json` = VALUES(`config_json`),
    `doc_link` = VALUES(`doc_link`),
    `remark` = VALUES(`remark`),
    `sort` = VALUES(`sort`),
    `updater` = VALUES(`updater`),
    `update_date` = NOW();
