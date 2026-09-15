package xiaozhi.modules.knowledge.service.impl;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Pattern;

import org.apache.commons.lang3.StringUtils;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

import xiaozhi.common.exception.RenException;
import xiaozhi.modules.knowledge.dto.dataset.DatasetDTO;
import xiaozhi.modules.knowledge.dto.document.DocumentDTO;

final class RAGFlowParserSettings {

    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final Pattern PIPELINE_ID_PATTERN = Pattern.compile("^[0-9a-fA-F]{32}$");

    private static final Set<String> ALLOWED_CHUNK_METHODS = Set.of(
            "naive",
            "manual",
            "qa",
            "table",
            "paper",
            "book",
            "laws",
            "presentation",
            "picture",
            "one",
            "knowledge_graph",
            "email",
            "tag");

    private static final Set<String> DOCUMENT_PARSER_CONFIG_KEYS = Set.of(
            "chunk_token_num",
            "delimiter",
            "layout_recognize",
            "auto_keywords",
            "auto_questions",
            "html4excel");

    private static final Set<String> DATASET_DIRECT_PARSER_CONFIG_KEYS = Set.of(
            "chunk_token_num",
            "delimiter",
            "layout_recognize",
            "auto_keywords",
            "auto_questions",
            "html4excel",
            "tag_kb_ids",
            "topn_tags",
            "filename_embd_weight",
            "task_page_size",
            "pages",
            "raptor",
            "graphrag");

    private static final Set<String> DATASET_EXT_PARSER_CONFIG_KEYS = Set.of(
            "toc_extraction",
            "image_table_context_window",
            "image_context_size",
            "table_context_size",
            "overlapped_percent",
            "enable_children",
            "children_delimiter",
            "metadata",
            "built_in_metadata",
            "enable_metadata",
            "field_map",
            "mineru_parse_method",
            "parse_method",
            "model_type");

    private RAGFlowParserSettings() {
    }

    static DatasetParserSettings normalizeDatasetSettings(String chunkMethod, String parserConfigJson,
            Integer parseType, String pipelineId, boolean defaultToNaive) {
        boolean pipelineMode = parseType != null || StringUtils.isNotBlank(pipelineId);
        if (pipelineMode) {
            Integer normalizedParseType = normalizeParseType(parseType);
            String normalizedPipelineId = normalizePipelineId(pipelineId);
            return DatasetParserSettings.pipeline(normalizedParseType, normalizedPipelineId);
        }

        String normalizedChunkMethod = normalizeChunkMethod(chunkMethod, defaultToNaive);
        DatasetDTO.ParserConfig parserConfig = normalizeDatasetParserConfig(parserConfigJson);
        return DatasetParserSettings.builtin(normalizedChunkMethod, parserConfig);
    }

    static String normalizeChunkMethod(String chunkMethod, boolean defaultToNaive) {
        if (StringUtils.isBlank(chunkMethod)) {
            return defaultToNaive ? "naive" : null;
        }

        String normalized = chunkMethod.trim().toLowerCase(Locale.ROOT);
        if (!ALLOWED_CHUNK_METHODS.contains(normalized)) {
            throw new RenException("不支持的 RAGFlow 解析模式: " + chunkMethod);
        }
        return normalized;
    }

    static String normalizeDatasetCreateChunkMethod(String chunkMethod) {
        return normalizeChunkMethod(chunkMethod, true);
    }

    static DatasetDTO.ParserConfig normalizeDatasetParserConfig(String parserConfigJson) {
        Map<String, Object> configMap = parseParserConfigJson(parserConfigJson);
        Map<String, Object> normalized = normalizeDatasetParserConfigMap(configMap);
        if (normalized.isEmpty()) {
            return null;
        }
        return toDatasetParserConfig(normalized);
    }

    static Map<String, Object> parseParserConfigJson(String parserConfigJson) {
        if (StringUtils.isBlank(parserConfigJson)) {
            return Collections.emptyMap();
        }
        try {
            return OBJECT_MAPPER.readValue(parserConfigJson, new TypeReference<Map<String, Object>>() {
            });
        } catch (Exception e) {
            throw new RenException("parserConfig 必须是合法的 JSON 对象");
        }
    }

    static Map<String, Object> normalizeParserConfigMap(Map<String, Object> parserConfig) {
        return normalizeDocumentParserConfigMap(parserConfig, true);
    }

    static Map<String, Object> normalizeDatasetParserConfigMap(Map<String, Object> parserConfig) {
        if (parserConfig == null || parserConfig.isEmpty()) {
            return Collections.emptyMap();
        }

        Map<String, Object> normalized = new LinkedHashMap<>();
        Map<String, Object> ext = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : parserConfig.entrySet()) {
            String key = entry.getKey();
            if (!DATASET_DIRECT_PARSER_CONFIG_KEYS.contains(key) && !DATASET_EXT_PARSER_CONFIG_KEYS.contains(key)
                    && !"ext".equals(key)) {
                throw new RenException("不支持的 RAGFlow parser_config 字段: " + key);
            }

            Object value = entry.getValue();
            if (value == null) {
                continue;
            }

            switch (key) {
                case "chunk_token_num" -> normalized.put(key, positiveInteger(key, value));
                case "delimiter" -> normalized.put(key, stringValue(key, value));
                case "layout_recognize" -> normalized.put(key, layoutRecognize(value));
                case "auto_keywords", "auto_questions" -> normalized.put(key, nonNegativeInteger(key, value));
                case "html4excel" -> normalized.put(key, booleanValue(key, value));
                case "tag_kb_ids" -> normalized.put(key, stringListValue(key, value));
                case "topn_tags" -> normalized.put(key, integerInRange(key, value, 1, 10));
                case "filename_embd_weight" -> normalized.put(key, doubleInRange(key, value, 0D, 1D));
                case "task_page_size" -> normalized.put(key, positiveInteger(key, value));
                case "pages" -> normalized.put(key, pagesValue(key, value));
                case "raptor" -> normalized.put(key, raptorConfig(value));
                case "graphrag" -> normalized.put(key, graphRagConfig(value));
                case "image_table_context_window" -> {
                    Integer size = nonNegativeInteger(key, value);
                    ext.put("image_table_context_window", size);
                    ext.put("image_context_size", size);
                    ext.put("table_context_size", size);
                }
                case "image_context_size", "table_context_size" -> ext.put(key, nonNegativeInteger(key, value));
                case "toc_extraction", "enable_children", "enable_metadata" -> ext.put(key, booleanValue(key, value));
                case "overlapped_percent" -> ext.put(key, doubleInRange(key, value, 0D, 1D));
                case "children_delimiter", "mineru_parse_method", "parse_method", "model_type" -> ext.put(key,
                        stringValue(key, value));
                case "metadata", "built_in_metadata", "field_map" -> ext.put(key, value);
                case "ext" -> ext.putAll(mapValue(key, value));
                default -> throw new RenException("不支持的 RAGFlow parser_config 字段: " + key);
            }
        }
        if (!ext.isEmpty()) {
            normalized.put("ext", ext);
        }
        return normalized;
    }

    static Map<String, Object> normalizeStoredParserConfigMap(Map<String, Object> parserConfig) {
        if (parserConfig == null || parserConfig.isEmpty()) {
            return Collections.emptyMap();
        }

        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : parserConfig.entrySet()) {
            if (!DOCUMENT_PARSER_CONFIG_KEYS.contains(entry.getKey()) || entry.getValue() == null) {
                continue;
            }
            try {
                Map<String, Object> singleField = Collections.singletonMap(entry.getKey(), entry.getValue());
                normalized.putAll(normalizeParserConfigMap(singleField));
            } catch (RenException ignored) {
                // Stored configs can include legacy or RAGFlow-returned values; do not block uploads on them.
            }
        }
        return normalized;
    }

    static DatasetDTO.ParserConfig toDatasetParserConfig(Map<String, Object> parserConfig) {
        if (parserConfig == null || parserConfig.isEmpty()) {
            return null;
        }
        DatasetDTO.ParserConfig config = new DatasetDTO.ParserConfig();
        config.setChunkTokenNum((Integer) parserConfig.get("chunk_token_num"));
        config.setDelimiter((String) parserConfig.get("delimiter"));
        config.setLayoutRecognize((String) parserConfig.get("layout_recognize"));
        config.setAutoKeywords((Integer) parserConfig.get("auto_keywords"));
        config.setAutoQuestions((Integer) parserConfig.get("auto_questions"));
        config.setHtml4excel((Boolean) parserConfig.get("html4excel"));
        config.setTagKbIds(castStringList(parserConfig.get("tag_kb_ids")));
        config.setTopnTags((Integer) parserConfig.get("topn_tags"));
        config.setFilenameEmbdWeight((Double) parserConfig.get("filename_embd_weight"));
        config.setTaskPageSize((Integer) parserConfig.get("task_page_size"));
        config.setPages(castPages(parserConfig.get("pages")));
        config.setRaptor(toRaptorConfig(castMap(parserConfig.get("raptor"))));
        config.setGraphRag(toGraphRagConfig(castMap(parserConfig.get("graphrag"))));
        config.setExt(castMap(parserConfig.get("ext")));
        return config;
    }

    static DocumentDTO.InfoVO.ParserConfig toDocumentParserConfig(Map<String, Object> parserConfig) {
        if (parserConfig == null || parserConfig.isEmpty()) {
            return null;
        }
        DocumentDTO.InfoVO.ParserConfig config = new DocumentDTO.InfoVO.ParserConfig();
        config.setChunkTokenNum((Integer) parserConfig.get("chunk_token_num"));
        config.setDelimiter((String) parserConfig.get("delimiter"));
        if (parserConfig.containsKey("layout_recognize")) {
            String layoutRecognize = (String) parserConfig.get("layout_recognize");
            if ("DeepDOC".equals(layoutRecognize) || "Simple".equals(layoutRecognize)) {
                config.setLayoutRecognize(DocumentDTO.InfoVO.LayoutRecognize.valueOf(layoutRecognize));
            }
        }
        config.setAutoKeywords((Integer) parserConfig.get("auto_keywords"));
        config.setAutoQuestions((Integer) parserConfig.get("auto_questions"));
        config.setHtml4excel((Boolean) parserConfig.get("html4excel"));
        return config;
    }

    private static Map<String, Object> normalizeDocumentParserConfigMap(Map<String, Object> parserConfig,
            boolean rejectUnknown) {
        if (parserConfig == null || parserConfig.isEmpty()) {
            return Collections.emptyMap();
        }

        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : parserConfig.entrySet()) {
            String key = entry.getKey();
            if (!DOCUMENT_PARSER_CONFIG_KEYS.contains(key)) {
                if (rejectUnknown) {
                    throw new RenException("不支持的 RAGFlow parser_config 字段: " + key);
                }
                continue;
            }

            Object value = entry.getValue();
            if (value == null) {
                continue;
            }

            switch (key) {
                case "chunk_token_num" -> normalized.put(key, positiveInteger(key, value));
                case "delimiter" -> normalized.put(key, stringValue(key, value));
                case "layout_recognize" -> normalized.put(key, layoutRecognize(value));
                case "auto_keywords", "auto_questions" -> normalized.put(key, nonNegativeInteger(key, value));
                case "html4excel" -> normalized.put(key, booleanValue(key, value));
                default -> {
                    if (rejectUnknown) {
                        throw new RenException("不支持的 RAGFlow parser_config 字段: " + key);
                    }
                }
            }
        }
        return normalized;
    }

    private static Integer positiveInteger(String key, Object value) {
        Integer integer = integerValue(key, value);
        if (integer <= 0) {
            throw new RenException(key + " 必须大于 0");
        }
        return integer;
    }

    private static Integer nonNegativeInteger(String key, Object value) {
        Integer integer = integerValue(key, value);
        if (integer < 0) {
            throw new RenException(key + " 不能小于 0");
        }
        return integer;
    }

    private static Integer integerInRange(String key, Object value, int min, int max) {
        Integer integer = integerValue(key, value);
        if (integer < min || integer > max) {
            throw new RenException(key + " 必须在 " + min + " 到 " + max + " 之间");
        }
        return integer;
    }

    private static Integer integerValue(String key, Object value) {
        if (value instanceof Number number) {
            double doubleValue = number.doubleValue();
            if (doubleValue % 1 != 0) {
                throw new RenException(key + " 必须是整数");
            }
            return number.intValue();
        }
        if (value instanceof String text && StringUtils.isNotBlank(text)) {
            try {
                return Integer.parseInt(text.trim());
            } catch (NumberFormatException ignored) {
                throw new RenException(key + " 必须是整数");
            }
        }
        throw new RenException(key + " 必须是整数");
    }

    private static Double doubleInRange(String key, Object value, double min, double max) {
        Double doubleValue = doubleValue(key, value);
        if (doubleValue < min || doubleValue > max) {
            throw new RenException(key + " 必须在 " + min + " 到 " + max + " 之间");
        }
        return doubleValue;
    }

    private static Double doubleValue(String key, Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value instanceof String text && StringUtils.isNotBlank(text)) {
            try {
                return Double.parseDouble(text.trim());
            } catch (NumberFormatException ignored) {
                throw new RenException(key + " 必须是数字");
            }
        }
        throw new RenException(key + " 必须是数字");
    }

    private static Boolean booleanValue(String key, Object value) {
        if (value instanceof Boolean bool) {
            return bool;
        }
        if (value instanceof String text) {
            String normalized = text.trim().toLowerCase(Locale.ROOT);
            if ("true".equals(normalized)) {
                return true;
            }
            if ("false".equals(normalized)) {
                return false;
            }
        }
        throw new RenException(key + " 必须是布尔值");
    }

    private static String stringValue(String key, Object value) {
        if (!(value instanceof String text)) {
            throw new RenException(key + " 必须是字符串");
        }
        return text;
    }

    private static String layoutRecognize(Object value) {
        if (!(value instanceof String text) || StringUtils.isBlank(text)) {
            throw new RenException("layout_recognize 不能为空");
        }
        if ("deepdoc".equalsIgnoreCase(text)) {
            return "DeepDOC";
        }
        if ("simple".equalsIgnoreCase(text)) {
            return "Simple";
        }
        if ("plain text".equalsIgnoreCase(text) || "plaintext".equalsIgnoreCase(text)) {
            return "Plain Text";
        }
        return text.trim();
    }

    private static Integer normalizeParseType(Integer parseType) {
        if (parseType == null) {
            throw new RenException("pipeline 模式必须设置 parseType");
        }
        if (parseType < 0 || parseType > 64) {
            throw new RenException("parseType 必须在 0 到 64 之间");
        }
        return parseType;
    }

    private static String normalizePipelineId(String pipelineId) {
        if (StringUtils.isBlank(pipelineId)) {
            throw new RenException("pipeline 模式必须设置 pipelineId");
        }
        String normalized = pipelineId.trim().toLowerCase(Locale.ROOT);
        if (!PIPELINE_ID_PATTERN.matcher(normalized).matches()) {
            throw new RenException("pipelineId 必须是 32 位十六进制字符串");
        }
        return normalized;
    }

    private static List<String> stringListValue(String key, Object value) {
        if (!(value instanceof List<?> list)) {
            throw new RenException(key + " 必须是字符串数组");
        }
        List<String> result = new ArrayList<>();
        for (Object item : list) {
            if (!(item instanceof String text) || StringUtils.isBlank(text)) {
                throw new RenException(key + " 必须是字符串数组");
            }
            result.add(text.trim());
        }
        return result;
    }

    private static List<List<Integer>> pagesValue(String key, Object value) {
        if (!(value instanceof List<?> ranges)) {
            throw new RenException(key + " 必须是页码范围数组");
        }
        List<List<Integer>> result = new ArrayList<>();
        for (Object range : ranges) {
            if (!(range instanceof List<?> pair) || pair.size() != 2) {
                throw new RenException(key + " 必须是形如 [[1, 10]] 的页码范围数组");
            }
            List<Integer> normalizedPair = new ArrayList<>(2);
            normalizedPair.add(positiveInteger(key, pair.get(0)));
            normalizedPair.add(positiveInteger(key, pair.get(1)));
            result.add(normalizedPair);
        }
        return result;
    }

    private static Map<String, Object> raptorConfig(Object value) {
        Map<String, Object> input = mapValue("raptor", value);
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : input.entrySet()) {
            String key = entry.getKey();
            Object item = entry.getValue();
            if (item == null) {
                continue;
            }
            switch (key) {
                case "use_raptor", "auto_disable_for_structured_data" -> normalized.put(key, booleanValue(key, item));
                case "prompt" -> normalized.put(key, stringValue(key, item));
                case "max_token" -> normalized.put(key, integerInRange(key, item, 1, 2048));
                case "threshold" -> normalized.put(key, doubleInRange(key, item, 0D, 1D));
                case "max_cluster" -> normalized.put(key, integerInRange(key, item, 1, 1024));
                case "random_seed" -> normalized.put(key, nonNegativeInteger(key, item));
                case "ext" -> normalized.put(key, mapValue(key, item));
                default -> throw new RenException("不支持的 RAGFlow raptor 字段: " + key);
            }
        }
        return normalized;
    }

    private static Map<String, Object> graphRagConfig(Object value) {
        Map<String, Object> input = mapValue("graphrag", value);
        Map<String, Object> normalized = new LinkedHashMap<>();
        for (Map.Entry<String, Object> entry : input.entrySet()) {
            String key = entry.getKey();
            Object item = entry.getValue();
            if (item == null) {
                continue;
            }
            switch (key) {
                case "use_graphrag", "community", "resolution" -> normalized.put(key, booleanValue(key, item));
                case "entity_types" -> normalized.put(key, stringListValue(key, item));
                case "method" -> normalized.put(key, graphRagMethod(item));
                default -> throw new RenException("不支持的 RAGFlow graphrag 字段: " + key);
            }
        }
        return normalized;
    }

    private static String graphRagMethod(Object value) {
        String method = stringValue("method", value).trim().toLowerCase(Locale.ROOT);
        if (!"light".equals(method) && !"general".equals(method)) {
            throw new RenException("graphrag.method 必须是 light 或 general");
        }
        return method;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> mapValue(String key, Object value) {
        if (!(value instanceof Map<?, ?> input)) {
            throw new RenException(key + " 必须是 JSON 对象");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        for (Map.Entry<?, ?> entry : input.entrySet()) {
            if (!(entry.getKey() instanceof String field)) {
                throw new RenException(key + " 字段名必须是字符串");
            }
            result.put(field, entry.getValue());
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> castMap(Object value) {
        if (value instanceof Map<?, ?> input) {
            Map<String, Object> result = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : input.entrySet()) {
                if (entry.getKey() instanceof String key) {
                    result.put(key, entry.getValue());
                }
            }
            return result;
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    private static List<String> castStringList(Object value) {
        if (value instanceof List<?> list) {
            List<String> result = new ArrayList<>();
            for (Object item : list) {
                if (item instanceof String text) {
                    result.add(text);
                }
            }
            return result;
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    private static List<List<Integer>> castPages(Object value) {
        if (value instanceof List<?> list) {
            List<List<Integer>> result = new ArrayList<>();
            for (Object item : list) {
                if (item instanceof List<?> pair) {
                    List<Integer> normalizedPair = new ArrayList<>();
                    for (Object page : pair) {
                        if (page instanceof Integer integer) {
                            normalizedPair.add(integer);
                        }
                    }
                    result.add(normalizedPair);
                }
            }
            return result;
        }
        return null;
    }

    private static DatasetDTO.ParserConfig.RaptorConfig toRaptorConfig(Map<String, Object> value) {
        if (value == null || value.isEmpty()) {
            return null;
        }
        DatasetDTO.ParserConfig.RaptorConfig config = new DatasetDTO.ParserConfig.RaptorConfig();
        config.setUseRaptor((Boolean) value.get("use_raptor"));
        config.setPrompt((String) value.get("prompt"));
        config.setMaxToken((Integer) value.get("max_token"));
        config.setThreshold((Double) value.get("threshold"));
        config.setMaxCluster((Integer) value.get("max_cluster"));
        config.setRandomSeed((Integer) value.get("random_seed"));
        config.setAutoDisableForStructuredData((Boolean) value.get("auto_disable_for_structured_data"));
        config.setExt(castMap(value.get("ext")));
        return config;
    }

    private static DatasetDTO.ParserConfig.GraphRagConfig toGraphRagConfig(Map<String, Object> value) {
        if (value == null || value.isEmpty()) {
            return null;
        }
        DatasetDTO.ParserConfig.GraphRagConfig config = new DatasetDTO.ParserConfig.GraphRagConfig();
        config.setUseGraphRag((Boolean) value.get("use_graphrag"));
        config.setEntityTypes(castStringList(value.get("entity_types")));
        config.setMethod((String) value.get("method"));
        config.setCommunity((Boolean) value.get("community"));
        config.setResolution((Boolean) value.get("resolution"));
        return config;
    }

    static final class DatasetParserSettings {
        private final boolean pipelineMode;
        private final String chunkMethod;
        private final DatasetDTO.ParserConfig parserConfig;
        private final Integer parseType;
        private final String pipelineId;

        private DatasetParserSettings(boolean pipelineMode, String chunkMethod,
                DatasetDTO.ParserConfig parserConfig, Integer parseType, String pipelineId) {
            this.pipelineMode = pipelineMode;
            this.chunkMethod = chunkMethod;
            this.parserConfig = parserConfig;
            this.parseType = parseType;
            this.pipelineId = pipelineId;
        }

        static DatasetParserSettings builtin(String chunkMethod, DatasetDTO.ParserConfig parserConfig) {
            return new DatasetParserSettings(false, chunkMethod, parserConfig, null, null);
        }

        static DatasetParserSettings pipeline(Integer parseType, String pipelineId) {
            return new DatasetParserSettings(true, null, null, parseType, pipelineId);
        }

        boolean isPipelineMode() {
            return pipelineMode;
        }

        String getChunkMethod() {
            return chunkMethod;
        }

        DatasetDTO.ParserConfig getParserConfig() {
            return parserConfig;
        }

        Integer getParseType() {
            return parseType;
        }

        String getPipelineId() {
            return pipelineId;
        }
    }
}
