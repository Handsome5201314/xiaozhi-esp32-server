package xiaozhi.modules.knowledge.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.LinkedHashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

import xiaozhi.common.exception.RenException;
import xiaozhi.modules.knowledge.dto.dataset.DatasetDTO;
import xiaozhi.modules.knowledge.dto.document.DocumentDTO;

class RAGFlowParserSettingsTest {

    @Test
    void keepsMissingParserConfigUnsetAndDefaultsChunkMethodToNaiveOnlyWhenNeeded() {
        assertNull(RAGFlowParserSettings.normalizeChunkMethod(null, false));
        assertEquals("naive", RAGFlowParserSettings.normalizeChunkMethod(null, true));
        assertEquals("naive", RAGFlowParserSettings.normalizeDatasetCreateChunkMethod(null));
        assertNull(RAGFlowParserSettings.normalizeDatasetParserConfig(null));
        assertTrue(RAGFlowParserSettings.normalizeParserConfigMap(null).isEmpty());
    }

    @Test
    void acceptsAllowedDatasetParserFields() {
        String json = """
                {
                  "chunk_token_num": 1024,
                  "delimiter": "\\n",
                  "layout_recognize": "DeepDOC",
                  "auto_keywords": 3,
                  "auto_questions": 2,
                  "html4excel": true
                }
                """;

        DatasetDTO.ParserConfig config = RAGFlowParserSettings.normalizeDatasetParserConfig(json);

        assertEquals(1024, config.getChunkTokenNum());
        assertEquals("\n", config.getDelimiter());
        assertEquals("DeepDOC", config.getLayoutRecognize());
        assertEquals(3, config.getAutoKeywords());
        assertEquals(2, config.getAutoQuestions());
        assertTrue(config.getHtml4excel());
    }

    @Test
    void rejectsUnknownParserFieldsAndUnknownChunkMethods() {
        assertThrows(RenException.class,
                () -> RAGFlowParserSettings.normalizeChunkMethod("not_a_method", false));
        assertThrows(RenException.class,
                () -> RAGFlowParserSettings.normalizeDatasetParserConfig("{\"not_supported\":3}"));
    }

    @Test
    void normalizesParserConfigMapForDocumentUpload() {
        Map<String, Object> parserConfig = new LinkedHashMap<>();
        parserConfig.put("chunk_token_num", 512);
        parserConfig.put("layout_recognize", "Simple");
        parserConfig.put("auto_keywords", 0);
        parserConfig.put("html4excel", false);

        Map<String, Object> normalized = RAGFlowParserSettings.normalizeParserConfigMap(parserConfig);
        DocumentDTO.InfoVO.ParserConfig documentConfig = RAGFlowParserSettings.toDocumentParserConfig(normalized);

        assertEquals(512, documentConfig.getChunkTokenNum());
        assertEquals(DocumentDTO.InfoVO.LayoutRecognize.Simple, documentConfig.getLayoutRecognize());
        assertEquals(0, documentConfig.getAutoKeywords());
        assertFalse(documentConfig.getHtml4excel());
    }

    @Test
    void filtersUnsupportedStoredParserFieldsForInheritance() {
        Map<String, Object> parserConfig = new LinkedHashMap<>();
        parserConfig.put("chunk_token_num", 512);
        parserConfig.put("layout_recognize", "DeepDOC");
        parserConfig.put("topn_tags", 3);

        Map<String, Object> normalized = RAGFlowParserSettings.normalizeStoredParserConfigMap(parserConfig);

        assertEquals(2, normalized.size());
        assertEquals(512, normalized.get("chunk_token_num"));
        assertEquals("DeepDOC", normalized.get("layout_recognize"));
        assertFalse(normalized.containsKey("topn_tags"));
    }

    @Test
    void pipelineModeRequiresParseTypeAndPipelineIdAndDoesNotSendBuiltinParserSettings() {
        RAGFlowParserSettings.DatasetParserSettings settings = RAGFlowParserSettings.normalizeDatasetSettings(
                "paper",
                "{\"chunk_token_num\":1024}",
                2,
                "0123456789abcdef0123456789abcdef",
                true);

        assertTrue(settings.isPipelineMode());
        assertNull(settings.getChunkMethod());
        assertNull(settings.getParserConfig());
        assertEquals(2, settings.getParseType());
        assertEquals("0123456789abcdef0123456789abcdef", settings.getPipelineId());

        assertThrows(RenException.class,
                () -> RAGFlowParserSettings.normalizeDatasetSettings(null, null, 2, null, true));
        assertThrows(RenException.class,
                () -> RAGFlowParserSettings.normalizeDatasetSettings(null, null, null,
                        "0123456789abcdef0123456789abcdef", true));
    }

    @Test
    void mapsExtendedParserFieldsToDatasetParserConfigAndExtPayload() {
        String json = """
                {
                  "chunk_token_num": 1024,
                  "layout_recognize": "Plain Text",
                  "tag_kb_ids": ["abc"],
                  "topn_tags": 3,
                  "filename_embd_weight": 0.2,
                  "task_page_size": 22,
                  "raptor": {
                    "use_raptor": true,
                    "max_token": 256,
                    "threshold": 0.1,
                    "max_cluster": 64,
                    "random_seed": 7,
                    "prompt": "summarize"
                  },
                  "graphrag": {
                    "use_graphrag": true,
                    "entity_types": ["organization", "person"],
                    "method": "light",
                    "community": true,
                    "resolution": true
                  },
                  "toc_extraction": true,
                  "image_table_context_window": 128,
                  "overlapped_percent": 0.2
                }
                """;

        DatasetDTO.ParserConfig config = RAGFlowParserSettings.normalizeDatasetParserConfig(json);

        assertEquals(1024, config.getChunkTokenNum());
        assertEquals("Plain Text", config.getLayoutRecognize());
        assertEquals(3, config.getTopnTags());
        assertEquals(0.2, config.getFilenameEmbdWeight());
        assertEquals(22, config.getTaskPageSize());
        assertEquals("abc", config.getTagKbIds().get(0));
        assertTrue(config.getRaptor().getUseRaptor());
        assertEquals("summarize", config.getRaptor().getPrompt());
        assertTrue(config.getGraphRag().getUseGraphRag());
        assertEquals("organization", config.getGraphRag().getEntityTypes().get(0));
        assertTrue((Boolean) config.getExt().get("toc_extraction"));
        assertEquals(128, config.getExt().get("image_table_context_window"));
        assertEquals(128, config.getExt().get("image_context_size"));
        assertEquals(128, config.getExt().get("table_context_size"));
        assertEquals(0.2, config.getExt().get("overlapped_percent"));
    }
}
