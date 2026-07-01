-- Create a ready-to-use demo agent for the Museum RAG guide scenario.
-- This makes the local demo reproducible after a fresh database init:
-- manager-api -> demo agent -> search_museum_knowledge plugin -> SuperMew RAG.
SET NAMES utf8mb4;

SET @museum_agent_id = 'museum_guide_agent_0000000001';
SET @museum_admin_user_id = (
    SELECT COALESCE(
        (SELECT `id` FROM `sys_user` WHERE `super_admin` = 1 ORDER BY `id` LIMIT 1),
        (SELECT `id` FROM `sys_user` ORDER BY `id` LIMIT 1),
        10001
    )
);

INSERT INTO `ai_agent` (
    `id`,
    `user_id`,
    `agent_code`,
    `agent_name`,
    `asr_model_id`,
    `vad_model_id`,
    `llm_model_id`,
    `slm_model_id`,
    `vllm_model_id`,
    `tts_model_id`,
    `tts_voice_id`,
    `tts_language`,
    `tts_volume`,
    `tts_rate`,
    `tts_pitch`,
    `mem_model_id`,
    `intent_model_id`,
    `system_prompt`,
    `summary_memory`,
    `chat_history_conf`,
    `lang_code`,
    `language`,
    `sort`,
    `creator`,
    `created_at`,
    `updater`,
    `updated_at`
)
SELECT
    @museum_agent_id,
    @museum_admin_user_id,
    '智博导览',
    '湖南省博物馆导览员',
    'ASR_FunASR',
    'VAD_SileroVAD',
    'LLM_ChatGLMLLM',
    NULL,
    'VLLM_ChatGLMVLLM',
    'TTS_EdgeTTS',
    'TTS_EdgeTTS0001',
    'zh',
    NULL,
    NULL,
    NULL,
    'Memory_nomem',
    'Intent_function_call',
    '你是“智博导览”的湖南省博物馆导览员。回答时优先调用博物馆知识库插件 search_museum_knowledge 检索资料，再基于检索结果进行讲解。讲解风格应准确、亲切、有导览感，适合对游客进行 1 到 3 分钟的口语化介绍。遇到马王堆汉墓、辛追夫人、素纱单衣、T 形帛画、皿方罍、人面纹方鼎、遗体防腐、展厅路线等问题时，必须优先依据知识库内容回答；如果知识库没有证据，应明确说明“资料中暂未检索到”。',
    NULL,
    1,
    'zh',
    '中文',
    0,
    @museum_admin_user_id,
    NOW(),
    @museum_admin_user_id,
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM `ai_agent` WHERE `id` = @museum_agent_id
);

UPDATE `ai_agent`
SET
    `user_id` = COALESCE(`user_id`, @museum_admin_user_id),
    `agent_code` = '智博导览',
    `agent_name` = '湖南省博物馆导览员',
    `intent_model_id` = 'Intent_function_call',
    `system_prompt` = '你是“智博导览”的湖南省博物馆导览员。回答时优先调用博物馆知识库插件 search_museum_knowledge 检索资料，再基于检索结果进行讲解。讲解风格应准确、亲切、有导览感，适合对游客进行 1 到 3 分钟的口语化介绍。遇到马王堆汉墓、辛追夫人、素纱单衣、T 形帛画、皿方罍、人面纹方鼎、遗体防腐、展厅路线等问题时，必须优先依据知识库内容回答；如果知识库没有证据，应明确说明“资料中暂未检索到”。',
    `updated_at` = NOW(),
    `updater` = @museum_admin_user_id
WHERE `id` = @museum_agent_id;

INSERT INTO `ai_agent_plugin_mapping` (
    `agent_id`,
    `plugin_id`,
    `param_info`
)
SELECT
    @museum_agent_id,
    'SYSTEM_PLUGIN_MUSEUM_KNOWLEDGE',
    JSON_OBJECT(
        'base_url', 'http://127.0.0.1:8000',
        'api_key', 'museum-rag-bridge-api-dev-key',
        'museum', '湖南省博物馆',
        'exhibition', '长沙马王堆汉墓陈列',
        'top_k', '3',
        'timeout', '30',
        'need_trace', 'true',
        'description', '当用户询问湖南省博物馆、马王堆汉墓、辛追夫人、素纱单衣、T形帛画、皿方罍、人面纹方鼎、遗体防腐或博物馆导览问题时调用本插件。'
    )
WHERE NOT EXISTS (
    SELECT 1
    FROM `ai_agent_plugin_mapping`
    WHERE `agent_id` = @museum_agent_id
      AND `plugin_id` = 'SYSTEM_PLUGIN_MUSEUM_KNOWLEDGE'
);

UPDATE `ai_agent_plugin_mapping`
SET `param_info` = JSON_SET(
    COALESCE(`param_info`, JSON_OBJECT()),
    '$.base_url', 'http://127.0.0.1:8000',
    '$.api_key', 'museum-rag-bridge-api-dev-key',
    '$.museum', '湖南省博物馆',
    '$.exhibition', '长沙马王堆汉墓陈列',
    '$.top_k', '3',
    '$.timeout', '30',
    '$.need_trace', 'true',
    '$.description', '当用户询问湖南省博物馆、马王堆汉墓、辛追夫人、素纱单衣、T形帛画、皿方罍、人面纹方鼎、遗体防腐或博物馆导览问题时调用本插件。'
)
WHERE `agent_id` = @museum_agent_id
  AND `plugin_id` = 'SYSTEM_PLUGIN_MUSEUM_KNOWLEDGE';
