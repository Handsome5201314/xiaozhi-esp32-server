package xiaozhi.modules.knowledge.service.impl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import org.junit.jupiter.api.Test;

import xiaozhi.modules.knowledge.entity.KnowledgeBaseEntity;

class KnowledgeBaseParserPersistenceTest {

    @Test
    void builtinUpdateClearsPipelineFieldsAndPersistsEmptyParserConfigAsUnset() {
        KnowledgeBaseEntity entity = new KnowledgeBaseEntity();
        entity.setChunkMethod("paper");
        entity.setParserConfig("{}");
        entity.setParseType(2);
        entity.setPipelineId("0123456789abcdef0123456789abcdef");

        RAGFlowParserSettings.DatasetParserSettings settings = RAGFlowParserSettings.normalizeDatasetSettings(
                "paper", "{}", null, null, false);

        KnowledgeBaseServiceImpl.applyParserSettingsToEntity(entity, "naive", "{\"chunk_token_num\":512}",
                2, "0123456789abcdef0123456789abcdef", true, true, settings);

        assertEquals("paper", entity.getChunkMethod());
        assertNull(entity.getParserConfig());
        assertNull(entity.getParseType());
        assertNull(entity.getPipelineId());
    }

    @Test
    void builtinChunkOnlyUpdatePreservesExistingParserConfigButClearsPipelineMode() {
        KnowledgeBaseEntity entity = new KnowledgeBaseEntity();
        entity.setChunkMethod("book");
        entity.setParserConfig(null);
        entity.setParseType(2);
        entity.setPipelineId("0123456789abcdef0123456789abcdef");

        RAGFlowParserSettings.DatasetParserSettings settings = RAGFlowParserSettings.normalizeDatasetSettings(
                "book", null, null, null, false);

        KnowledgeBaseServiceImpl.applyParserSettingsToEntity(entity, "paper", "{\"chunk_token_num\":512}",
                2, "0123456789abcdef0123456789abcdef", true, false, settings);

        assertEquals("book", entity.getChunkMethod());
        assertEquals("{\"chunk_token_num\":512}", entity.getParserConfig());
        assertNull(entity.getParseType());
        assertNull(entity.getPipelineId());
    }

    @Test
    void pipelineUpdateClearsBuiltinParserFields() {
        KnowledgeBaseEntity entity = new KnowledgeBaseEntity();
        entity.setChunkMethod("naive");
        entity.setParserConfig("{\"chunk_token_num\":512}");

        RAGFlowParserSettings.DatasetParserSettings settings = RAGFlowParserSettings.normalizeDatasetSettings(
                "naive", "{\"chunk_token_num\":512}", 2, "0123456789abcdef0123456789abcdef", false);

        KnowledgeBaseServiceImpl.applyParserSettingsToEntity(entity, "naive", "{\"chunk_token_num\":512}",
                null, null, true, false, settings);

        assertNull(entity.getChunkMethod());
        assertNull(entity.getParserConfig());
        assertEquals(2, entity.getParseType());
        assertEquals("0123456789abcdef0123456789abcdef", entity.getPipelineId());
    }
}
