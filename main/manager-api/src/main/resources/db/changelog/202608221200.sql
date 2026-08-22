UPDATE `ai_model_provider`
SET `fields` = '[{"key":"model_dir","label":"模型目录","type":"string"},{"key":"output_dir","label":"输出目录","type":"string"},{"key":"language","label":"识别语言","type":"string","default":"auto"},{"key":"device","label":"推理设备","type":"string","default":"cuda:0"}]'
WHERE `id` = 'SYSTEM_ASR_FunASR';

UPDATE `ai_model_config`
SET `config_json` = JSON_SET(`config_json`, '$.device', 'cuda:0')
WHERE `id` = 'ASR_FunASR';
