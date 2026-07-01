-- Sync the Museum RAG plugin bridge parameters for existing deployments.
-- Use UTF-8 hex literals to avoid Windows console/codepage corruption.
SET NAMES utf8mb4;

UPDATE `ai_model_provider`
SET `fields` = JSON_ARRAY(
    JSON_OBJECT('key','base_url','type','string','label',CONVERT(0xe58d9ae789a9e9a686e79fa5e8af86e5ba93e68ea5e58fa3e59cb0e59d80 USING utf8mb4),'default',CONVERT(0x687474703a2f2f3132372e302e302e313a38303030 USING utf8mb4)),
    JSON_OBJECT('key','api_key','type','string','label',CONVERT(0xe68ea5e58fa3e5af86e992a5 USING utf8mb4),'default',CONVERT(0x6d757365756d2d7261672d6272696467652d6170692d6465762d6b6579 USING utf8mb4)),
    JSON_OBJECT('key','museum','type','string','label',CONVERT(0xe58d9ae789a9e9a686e5908de7a7b0 USING utf8mb4),'default',CONVERT(0xe6b996e58d97e79c81e58d9ae789a9e9a686 USING utf8mb4)),
    JSON_OBJECT('key','exhibition','type','string','label',CONVERT(0xe5b195e8a788e5908de7a7b0 USING utf8mb4),'default',CONVERT(0xe995bfe6b299e9a9ace78e8be5a086e6b189e5a293e99988e58897 USING utf8mb4)),
    JSON_OBJECT('key','top_k','type','string','label',CONVERT(0xe6a380e7b4a2e78987e6aeb5e695b0 USING utf8mb4),'default',CONVERT(0x33 USING utf8mb4)),
    JSON_OBJECT('key','timeout','type','string','label',CONVERT(0xe8afb7e6b182e8b685e697b6e7a792e695b0 USING utf8mb4),'default',CONVERT(0x3330 USING utf8mb4)),
    JSON_OBJECT('key','need_trace','type','string','label',CONVERT(0xe8bf94e59b9ee6a380e7b4a2e8bfbde8b8aa USING utf8mb4),'default',CONVERT(0x74727565 USING utf8mb4)),
    JSON_OBJECT('key','description','type','string','label',CONVERT(0xe8b083e794a8e8afb4e6988e USING utf8mb4),'default',CONVERT(0xe5bd93e794a8e688b7e8afa2e997aee6b996e58d97e79c81e58d9ae789a9e9a686e38081e9a9ace78e8be5a086e6b189e5a293e38081e8be9be8bfbde5a4abe4babae38081e7b4a0e7bab1e58d95e8a1a3e3808154e5bda2e5b89be794bbe38081e79abfe696b9e7bd8de38081e4babae99da2e7bab9e696b9e9bc8ee38081e98197e4bd93e998b2e88590e68896e58d9ae789a9e9a686e5afbce8a788e997aee9a298e697b6e8b083e794a8e69cace68f92e4bbb6e38082 USING utf8mb4))
)
WHERE `id` = 'SYSTEM_PLUGIN_MUSEUM_KNOWLEDGE';

UPDATE `ai_agent_plugin_mapping`
SET `param_info` = JSON_SET(
    COALESCE(`param_info`, JSON_OBJECT()),
    '$.base_url', 'http://127.0.0.1:8000',
    '$.api_key', 'museum-rag-bridge-api-dev-key',
    '$.museum', CONVERT(0xe6b996e58d97e79c81e58d9ae789a9e9a686 USING utf8mb4),
    '$.exhibition', CONVERT(0xe995bfe6b299e9a9ace78e8be5a086e6b189e5a293e99988e58897 USING utf8mb4),
    '$.top_k', '3',
    '$.timeout', '30',
    '$.need_trace', 'true',
    '$.description', CONVERT(0xe5bd93e794a8e688b7e8afa2e997aee6b996e58d97e79c81e58d9ae789a9e9a686e38081e9a9ace78e8be5a086e6b189e5a293e38081e8be9be8bfbde5a4abe4babae38081e7b4a0e7bab1e58d95e8a1a3e3808154e5bda2e5b89be794bbe38081e79abfe696b9e7bd8de38081e4babae99da2e7bab9e696b9e9bc8ee38081e98197e4bd93e998b2e88590e68896e58d9ae789a9e9a686e5afbce8a788e997aee9a298e697b6e8b083e794a8e69cace68f92e4bbb6e38082 USING utf8mb4)
)
WHERE `plugin_id` = 'SYSTEM_PLUGIN_MUSEUM_KNOWLEDGE';
