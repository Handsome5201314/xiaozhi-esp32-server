<template>
  <el-dialog :title="title" :visible="dialogVisible" width="960px" class="knowledge-base-dialog" @close="handleClose">
    <el-form ref="knowledgeBaseForm" :model="form" :rules="rules" label-width="112px" size="medium">
      <section class="config-section">
        <div class="section-title">基础信息</div>
        <div class="section-grid section-grid-basic">
          <el-form-item :label="$t('knowledgeBaseDialog.name')" prop="name">
            <el-input v-model="form.name" :placeholder="$t('knowledgeBaseDialog.namePlaceholder')" clearable></el-input>
          </el-form-item>
          <el-form-item label="权限" prop="permission">
            <el-select v-model="form.permission" style="width: 100%">
              <el-option label="仅自己" value="me"></el-option>
              <el-option label="团队" value="team"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item :label="$t('knowledgeBaseDialog.ragModel')" prop="ragModelId">
            <el-select v-model="form.ragModelId" :placeholder="$t('knowledgeBaseDialog.ragModelPlaceholder')" clearable
              filterable style="width: 100%" @focus="loadRAGModels">
              <el-option v-for="model in ragModels" :key="model.id" :label="model.modelName" :value="model.id">
              </el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="嵌入模型">
            <el-input v-model="form.embeddingModel" placeholder="留空则使用 RAGFlow 默认嵌入模型" clearable></el-input>
          </el-form-item>
          <el-form-item :label="$t('knowledgeBaseDialog.description')" prop="description" class="grid-span-2">
            <el-input v-model="form.description" :placeholder="$t('knowledgeBaseDialog.descriptionPlaceholder')"
              type="textarea" :rows="3" maxlength="300" show-word-limit></el-input>
          </el-form-item>
          <el-form-item label="头像 Base64" class="grid-span-2">
            <el-input v-model="form.avatar" placeholder="可选，留空时沿用默认透明头像" type="textarea" :rows="2"></el-input>
          </el-form-item>
        </div>
      </section>

      <section class="config-section">
        <div class="section-title">Ingestion Pipeline</div>
        <el-form-item label="摄入方式">
          <el-radio-group v-model="parserMode" @change="handleParserModeChange">
            <el-radio-button label="builtin">内置解析</el-radio-button>
            <el-radio-button label="pipeline">选择 Pipeline</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <div v-if="parserMode === 'pipeline'" class="section-grid">
          <el-form-item label="Parse Type" required>
            <el-input-number v-model="pipelineForm.parseType" :min="0" :max="64" controls-position="right"
              @change="markPipelineDirty"></el-input-number>
          </el-form-item>
          <el-form-item label="Pipeline ID" required>
            <el-input v-model="pipelineForm.pipelineId" placeholder="32 位十六进制 Pipeline ID" clearable
              @input="markPipelineDirty"></el-input>
          </el-form-item>
        </div>

        <template v-else>
          <div class="section-grid">
            <el-form-item :label="$t('knowledgeBaseDialog.chunkMethod')" prop="chunkMethod">
              <el-select v-model="form.chunkMethod" :placeholder="$t('knowledgeBaseDialog.chunkMethodPlaceholder')"
                filterable style="width: 100%">
                <el-option v-for="method in chunkMethodOptions" :key="method.value" :label="method.label"
                  :value="method.value">
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="PDF 解析器">
              <el-select v-model="parserConfigForm.layoutRecognize" clearable placeholder="默认由 RAGFlow 决定"
                style="width: 100%" @change="markParserConfigDirty">
                <el-option label="DeepDOC" value="DeepDOC"></el-option>
                <el-option label="Plain Text" value="Plain Text"></el-option>
                <el-option label="Simple" value="Simple"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="建议块大小">
              <el-input-number v-model="parserConfigForm.chunkTokenNum" :min="1" :max="2048" :step="128"
                controls-position="right" placeholder="512" @change="markParserConfigDirty"></el-input-number>
            </el-form-item>
            <el-form-item :label="$t('knowledgeBaseDialog.delimiter')">
              <el-input v-model="parserConfigForm.delimiter" :placeholder="$t('knowledgeBaseDialog.delimiterPlaceholder')"
                clearable @input="markParserConfigDirty"></el-input>
            </el-form-item>
            <el-form-item label="图片/表格上下文">
              <el-input-number v-model="parserConfigForm.imageTableContextWindow" :min="0" :step="32"
                controls-position="right" @change="markParserConfigDirty"></el-input-number>
            </el-form-item>
            <el-form-item label="重叠比例">
              <el-input-number v-model="parserConfigForm.overlappedPercent" :min="0" :max="1" :step="0.05"
                controls-position="right" @change="markParserConfigDirty"></el-input-number>
            </el-form-item>
            <el-form-item :label="$t('knowledgeBaseDialog.autoKeywords')">
              <el-input-number v-model="parserConfigForm.autoKeywords" :min="0" :max="32" :step="1"
                controls-position="right" @change="markParserConfigDirty"></el-input-number>
            </el-form-item>
            <el-form-item :label="$t('knowledgeBaseDialog.autoQuestions')">
              <el-input-number v-model="parserConfigForm.autoQuestions" :min="0" :max="10" :step="1"
                controls-position="right" @change="markParserConfigDirty"></el-input-number>
            </el-form-item>
            <el-form-item label="目录提取">
              <el-switch v-model="parserConfigForm.tocExtraction" @change="markParserConfigDirty"></el-switch>
            </el-form-item>
            <el-form-item :label="$t('knowledgeBaseDialog.html4excel')">
              <el-switch v-model="parserConfigForm.html4excel" @change="handleHtml4excelChange"></el-switch>
            </el-form-item>
          </div>
        </template>
      </section>

      <section v-if="parserMode === 'builtin'" class="config-section">
        <div class="section-title">索引增强</div>
        <div class="section-grid">
          <el-form-item label="标签知识库">
            <el-input v-model="parserConfigForm.tagKbIds" placeholder="多个 ID 用逗号分隔" clearable
              @input="markParserConfigDirty"></el-input>
          </el-form-item>
          <el-form-item label="标签数量">
            <el-input-number v-model="parserConfigForm.topnTags" :min="1" :max="10" controls-position="right"
              @change="markParserConfigDirty"></el-input-number>
          </el-form-item>
          <el-form-item label="文件名权重">
            <el-input-number v-model="parserConfigForm.filenameEmbdWeight" :min="0" :max="1" :step="0.1"
              controls-position="right" @change="markParserConfigDirty"></el-input-number>
          </el-form-item>
          <el-form-item label="任务页大小">
            <el-input-number v-model="parserConfigForm.taskPageSize" :min="1" controls-position="right"
              @change="markParserConfigDirty"></el-input-number>
          </el-form-item>
        </div>

        <el-collapse v-model="advancedActive" class="advanced-collapse">
          <el-collapse-item title="RAPTOR" name="raptor">
            <div class="section-grid">
              <el-form-item label="启用 RAPTOR">
                <el-switch v-model="parserConfigForm.raptor.useRaptor" @change="handleRaptorChange"></el-switch>
              </el-form-item>
              <el-form-item label="最大 Token">
                <el-input-number v-model="parserConfigForm.raptor.maxToken" :min="1" :max="2048"
                  controls-position="right" @change="handleRaptorChange"></el-input-number>
              </el-form-item>
              <el-form-item label="阈值">
                <el-input-number v-model="parserConfigForm.raptor.threshold" :min="0" :max="1" :step="0.05"
                  controls-position="right" @change="handleRaptorChange"></el-input-number>
              </el-form-item>
              <el-form-item label="最大聚类">
                <el-input-number v-model="parserConfigForm.raptor.maxCluster" :min="1" :max="1024"
                  controls-position="right" @change="handleRaptorChange"></el-input-number>
              </el-form-item>
              <el-form-item label="随机种子">
                <el-input-number v-model="parserConfigForm.raptor.randomSeed" :min="0" controls-position="right"
                  @change="handleRaptorChange"></el-input-number>
              </el-form-item>
              <el-form-item label="摘要提示词" class="grid-span-2">
                <el-input v-model="parserConfigForm.raptor.prompt" type="textarea" :rows="2"
                  @input="handleRaptorChange"></el-input>
              </el-form-item>
            </div>
          </el-collapse-item>

          <el-collapse-item title="GraphRAG" name="graphrag">
            <div class="section-grid">
              <el-form-item label="启用 GraphRAG">
                <el-switch v-model="parserConfigForm.graphRag.useGraphRag" @change="handleGraphRagChange"></el-switch>
              </el-form-item>
              <el-form-item label="构建方法">
                <el-select v-model="parserConfigForm.graphRag.method" style="width: 100%" @change="handleGraphRagChange">
                  <el-option label="Light" value="light"></el-option>
                  <el-option label="General" value="general"></el-option>
                </el-select>
              </el-form-item>
              <el-form-item label="实体类型" class="grid-span-2">
                <el-input v-model="parserConfigForm.graphRag.entityTypes" placeholder="organization, person, geo, event"
                  clearable @input="handleGraphRagChange"></el-input>
              </el-form-item>
              <el-form-item label="社区发现">
                <el-switch v-model="parserConfigForm.graphRag.community" @change="handleGraphRagChange"></el-switch>
              </el-form-item>
              <el-form-item label="实体消歧">
                <el-switch v-model="parserConfigForm.graphRag.resolution" @change="handleGraphRagChange"></el-switch>
              </el-form-item>
            </div>
          </el-collapse-item>
        </el-collapse>
      </section>
    </el-form>

    <div slot="footer" class="dialog-footer">
      <el-button @click="handleClose">{{ $t('knowledgeBaseDialog.cancel') }}</el-button>
      <el-button type="primary" @click="handleSubmit">{{ $t('knowledgeBaseDialog.confirm') }}</el-button>
    </div>
  </el-dialog>
</template>

<script>
import Api from "@/apis/api";

const DEFAULT_RAPTOR_PROMPT = "Please summarize the following paragraphs. Be careful with the numbers, do not make things up. Paragraphs as following:\n      {cluster_content}\nThe above is the content you need to summarize.";

const createDefaultParserConfigForm = () => ({
  chunkTokenNum: null,
  delimiter: "",
  layoutRecognize: "",
  imageTableContextWindow: null,
  overlappedPercent: null,
  autoKeywords: null,
  autoQuestions: null,
  html4excel: false,
  tocExtraction: false,
  tagKbIds: "",
  topnTags: null,
  filenameEmbdWeight: null,
  taskPageSize: null,
  raptor: {
    useRaptor: false,
    maxToken: null,
    threshold: null,
    maxCluster: null,
    randomSeed: null,
    prompt: DEFAULT_RAPTOR_PROMPT
  },
  graphRag: {
    useGraphRag: false,
    entityTypes: "organization, person, geo, event, category",
    method: "light",
    community: false,
    resolution: false
  }
});

export default {
  name: "KnowledgeBaseDialog",
  props: {
    title: {
      type: String,
      default: ""
    },
    visible: {
      type: Boolean,
      default: false
    },
    form: {
      type: Object,
      default: () => ({
        id: null,
        datasetId: null,
        ragModelId: null,
        name: "",
        description: "",
        permission: "me",
        embeddingModel: "",
        avatar: "",
        chunkMethod: "naive",
        parseType: null,
        pipelineId: "",
        parserConfig: null
      })
    }
  },
  data() {
    return {
      dialogVisible: this.visible,
      ragModels: [],
      parserMode: "builtin",
      parserConfigDirty: false,
      pipelineDirty: false,
      html4excelKnown: false,
      raptorKnown: false,
      graphRagKnown: false,
      advancedActive: [],
      pipelineForm: {
        parseType: 2,
        pipelineId: ""
      },
      parserConfigForm: createDefaultParserConfigForm(),
      chunkMethodOptions: [
        { label: this.$t("knowledgeBaseDialog.chunkMethodNaive"), value: "naive" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodPaper"), value: "paper" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodTable"), value: "table" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodQa"), value: "qa" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodBook"), value: "book" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodLaws"), value: "laws" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodPresentation"), value: "presentation" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodPicture"), value: "picture" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodOne"), value: "one" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodManual"), value: "manual" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodKnowledgeGraph"), value: "knowledge_graph" },
        { label: this.$t("knowledgeBaseDialog.chunkMethodEmail"), value: "email" }
      ],
      rules: {
        name: [
          { required: true, message: this.$t("knowledgeBaseDialog.nameRequired"), trigger: "blur" },
          { min: 1, max: 50, message: this.$t("knowledgeBaseDialog.nameLength"), trigger: "blur" },
          {
            pattern: /^[\u4e00-\u9fa5a-zA-Z0-9\s-_]+$/,
            message: this.$t("knowledgeBaseDialog.namePattern"),
            trigger: "blur"
          }
        ],
        description: [
          { required: true, message: this.$t("knowledgeBaseDialog.descriptionRequired"), trigger: "blur" },
          { max: 300, message: this.$t("knowledgeBaseDialog.descriptionLength"), trigger: "blur" }
        ],
        ragModelId: [
          { required: true, message: this.$t("knowledgeBaseDialog.ragModelRequired"), trigger: "change" }
        ],
        chunkMethod: [
          { required: true, message: this.$t("knowledgeBaseDialog.chunkMethodRequired"), trigger: "change" }
        ]
      }
    };
  },
  watch: {
    visible(val) {
      this.dialogVisible = val;
      if (val) {
        this.initializeFormDefaults();
        this.initializeParserSettings();
        this.loadRAGModels();
        if (this.$refs.knowledgeBaseForm) {
          this.$refs.knowledgeBaseForm.clearValidate();
        }
      }
    },
    ragModels(newModels) {
      if (newModels.length > 0 && !this.form.id && !this.form.ragModelId) {
        this.$set(this.form, "ragModelId", newModels[0].id);
      }
    }
  },
  methods: {
    handleClose() {
      if (this.$refs.knowledgeBaseForm) {
        this.$refs.knowledgeBaseForm.clearValidate();
      }
      this.dialogVisible = false;
      this.$emit("update:visible", false);
    },
    handleSubmit() {
      this.$refs.knowledgeBaseForm.validate(valid => {
        if (!valid) {
          return;
        }
        if (this.parserMode === "pipeline" && !this.validatePipeline()) {
          return;
        }
        this.$emit("submit", this.buildSubmitForm());
      });
    },
    initializeFormDefaults() {
      if (!this.form.permission) {
        this.$set(this.form, "permission", "me");
      }
      if (!this.form.chunkMethod && !this.form.pipelineId) {
        this.$set(this.form, "chunkMethod", "naive");
      }
      if (this.form.embeddingModel === undefined) {
        this.$set(this.form, "embeddingModel", "");
      }
      if (this.form.avatar === undefined) {
        this.$set(this.form, "avatar", "");
      }
    },
    initializeParserSettings() {
      this.parserMode = this.form.pipelineId ? "pipeline" : "builtin";
      this.pipelineForm = {
        parseType: this.form.parseType !== null && this.form.parseType !== undefined ? Number(this.form.parseType) : 2,
        pipelineId: this.form.pipelineId || ""
      };
      this.pipelineDirty = false;
      this.parserConfigForm = createDefaultParserConfigForm();
      this.parserConfigDirty = false;
      this.html4excelKnown = false;
      this.raptorKnown = false;
      this.graphRagKnown = false;
      this.advancedActive = [];

      const parserConfig = this.parseExistingParserConfig(this.form.parserConfig);
      const extConfig = parserConfig.ext && typeof parserConfig.ext === "object" ? parserConfig.ext : {};
      let hasRaptor = false;
      let hasGraphRag = false;

      if (parserConfig.chunk_token_num !== undefined && parserConfig.chunk_token_num !== null) {
        this.parserConfigForm.chunkTokenNum = Number(parserConfig.chunk_token_num);
      }
      if (typeof parserConfig.delimiter === "string") {
        this.parserConfigForm.delimiter = this.formatDelimiterForInput(parserConfig.delimiter);
      }
      if (typeof parserConfig.layout_recognize === "string") {
        this.parserConfigForm.layoutRecognize = parserConfig.layout_recognize;
      }
      if (parserConfig.image_table_context_window !== undefined || extConfig.image_table_context_window !== undefined) {
        this.parserConfigForm.imageTableContextWindow = Number(
          parserConfig.image_table_context_window !== undefined
            ? parserConfig.image_table_context_window
            : extConfig.image_table_context_window
        );
      }
      if (parserConfig.overlapped_percent !== undefined || extConfig.overlapped_percent !== undefined) {
        this.parserConfigForm.overlappedPercent = Number(
          parserConfig.overlapped_percent !== undefined
            ? parserConfig.overlapped_percent
            : extConfig.overlapped_percent
        );
      }
      if (parserConfig.auto_keywords !== undefined && parserConfig.auto_keywords !== null) {
        this.parserConfigForm.autoKeywords = Number(parserConfig.auto_keywords);
      }
      if (parserConfig.auto_questions !== undefined && parserConfig.auto_questions !== null) {
        this.parserConfigForm.autoQuestions = Number(parserConfig.auto_questions);
      }
      if (typeof parserConfig.html4excel === "boolean") {
        this.parserConfigForm.html4excel = parserConfig.html4excel;
        this.html4excelKnown = true;
      }
      if (typeof parserConfig.toc_extraction === "boolean" || typeof extConfig.toc_extraction === "boolean") {
        this.parserConfigForm.tocExtraction = Boolean(
          parserConfig.toc_extraction !== undefined ? parserConfig.toc_extraction : extConfig.toc_extraction
        );
      }
      if (Array.isArray(parserConfig.tag_kb_ids)) {
        this.parserConfigForm.tagKbIds = parserConfig.tag_kb_ids.join(", ");
      }
      if (parserConfig.topn_tags !== undefined && parserConfig.topn_tags !== null) {
        this.parserConfigForm.topnTags = Number(parserConfig.topn_tags);
      }
      if (parserConfig.filename_embd_weight !== undefined && parserConfig.filename_embd_weight !== null) {
        this.parserConfigForm.filenameEmbdWeight = Number(parserConfig.filename_embd_weight);
      }
      if (parserConfig.task_page_size !== undefined && parserConfig.task_page_size !== null) {
        this.parserConfigForm.taskPageSize = Number(parserConfig.task_page_size);
      }
      if (parserConfig.raptor && typeof parserConfig.raptor === "object") {
        hasRaptor = true;
        this.raptorKnown = true;
        this.parserConfigForm.raptor.useRaptor = Boolean(parserConfig.raptor.use_raptor);
        this.parserConfigForm.raptor.maxToken = parserConfig.raptor.max_token !== undefined ? Number(parserConfig.raptor.max_token) : null;
        this.parserConfigForm.raptor.threshold = parserConfig.raptor.threshold !== undefined ? Number(parserConfig.raptor.threshold) : null;
        this.parserConfigForm.raptor.maxCluster = parserConfig.raptor.max_cluster !== undefined ? Number(parserConfig.raptor.max_cluster) : null;
        this.parserConfigForm.raptor.randomSeed = parserConfig.raptor.random_seed !== undefined ? Number(parserConfig.raptor.random_seed) : null;
        this.parserConfigForm.raptor.prompt = parserConfig.raptor.prompt || DEFAULT_RAPTOR_PROMPT;
      }
      if (parserConfig.graphrag && typeof parserConfig.graphrag === "object") {
        hasGraphRag = true;
        this.graphRagKnown = true;
        this.parserConfigForm.graphRag.useGraphRag = Boolean(parserConfig.graphrag.use_graphrag);
        this.parserConfigForm.graphRag.entityTypes = Array.isArray(parserConfig.graphrag.entity_types)
          ? parserConfig.graphrag.entity_types.join(", ")
          : this.parserConfigForm.graphRag.entityTypes;
        this.parserConfigForm.graphRag.method = parserConfig.graphrag.method || "light";
        this.parserConfigForm.graphRag.community = Boolean(parserConfig.graphrag.community);
        this.parserConfigForm.graphRag.resolution = Boolean(parserConfig.graphrag.resolution);
      }
      this.advancedActive = [
        ...(hasRaptor ? ["raptor"] : []),
        ...(hasGraphRag ? ["graphrag"] : [])
      ];
    },
    parseExistingParserConfig(parserConfig) {
      if (!parserConfig) {
        return {};
      }
      if (typeof parserConfig === "object") {
        return parserConfig;
      }
      try {
        const parsed = JSON.parse(parserConfig);
        return parsed && typeof parsed === "object" ? parsed : {};
      } catch (e) {
        return {};
      }
    },
    handleParserModeChange() {
      if (this.parserMode === "builtin" && !this.form.chunkMethod) {
        this.$set(this.form, "chunkMethod", "naive");
      }
    },
    markParserConfigDirty() {
      this.parserConfigDirty = true;
    },
    markPipelineDirty() {
      this.pipelineDirty = true;
    },
    handleHtml4excelChange() {
      this.html4excelKnown = true;
      this.markParserConfigDirty();
    },
    handleRaptorChange() {
      this.raptorKnown = true;
      this.markParserConfigDirty();
    },
    handleGraphRagChange() {
      this.graphRagKnown = true;
      this.markParserConfigDirty();
    },
    validatePipeline() {
      if (this.pipelineForm.parseType === null || this.pipelineForm.parseType === undefined) {
        this.$message.error("请选择 Pipeline 的 parse type");
        return false;
      }
      if (!/^[0-9a-fA-F]{32}$/.test(this.pipelineForm.pipelineId || "")) {
        this.$message.error("Pipeline ID 必须是 32 位十六进制字符串");
        return false;
      }
      return true;
    },
    buildSubmitForm() {
      const submitForm = { ...this.form };
      if (!submitForm.permission) {
        submitForm.permission = "me";
      }

      if (this.parserMode === "pipeline") {
        delete submitForm.chunkMethod;
        delete submitForm.parserConfig;
        submitForm.parseType = Number(this.pipelineForm.parseType);
        submitForm.pipelineId = this.pipelineForm.pipelineId;
        return this.pruneEmptyFields(submitForm);
      }

      submitForm.chunkMethod = this.form.chunkMethod || "naive";
      delete submitForm.parseType;
      delete submitForm.pipelineId;
      const parserConfig = this.buildParserConfigPayload();
      if (parserConfig) {
        submitForm.parserConfig = JSON.stringify(parserConfig);
      } else {
        delete submitForm.parserConfig;
      }
      return this.pruneEmptyFields(submitForm);
    },
    buildParserConfigPayload() {
      if (!this.parserConfigDirty) {
        return null;
      }

      const config = {};
      if (this.parserConfigForm.chunkTokenNum !== null && this.parserConfigForm.chunkTokenNum !== undefined) {
        config.chunk_token_num = Number(this.parserConfigForm.chunkTokenNum);
      }
      if (this.parserConfigForm.delimiter) {
        config.delimiter = this.parseDelimiterForPayload(this.parserConfigForm.delimiter);
      }
      if (this.parserConfigForm.layoutRecognize) {
        config.layout_recognize = this.parserConfigForm.layoutRecognize;
      }
      if (this.parserConfigForm.imageTableContextWindow !== null && this.parserConfigForm.imageTableContextWindow !== undefined) {
        config.image_table_context_window = Number(this.parserConfigForm.imageTableContextWindow);
      }
      if (this.parserConfigForm.overlappedPercent !== null && this.parserConfigForm.overlappedPercent !== undefined) {
        config.overlapped_percent = Number(this.parserConfigForm.overlappedPercent);
      }
      if (this.parserConfigForm.autoKeywords !== null && this.parserConfigForm.autoKeywords !== undefined) {
        config.auto_keywords = Number(this.parserConfigForm.autoKeywords);
      }
      if (this.parserConfigForm.autoQuestions !== null && this.parserConfigForm.autoQuestions !== undefined) {
        config.auto_questions = Number(this.parserConfigForm.autoQuestions);
      }
      if (this.html4excelKnown || this.parserConfigForm.html4excel === true) {
        config.html4excel = Boolean(this.parserConfigForm.html4excel);
      }
      if (this.parserConfigForm.tocExtraction === true) {
        config.toc_extraction = true;
      }
      const tagKbIds = this.splitList(this.parserConfigForm.tagKbIds);
      if (tagKbIds.length > 0) {
        config.tag_kb_ids = tagKbIds;
      }
      if (this.parserConfigForm.topnTags !== null && this.parserConfigForm.topnTags !== undefined) {
        config.topn_tags = Number(this.parserConfigForm.topnTags);
      }
      if (this.parserConfigForm.filenameEmbdWeight !== null && this.parserConfigForm.filenameEmbdWeight !== undefined) {
        config.filename_embd_weight = Number(this.parserConfigForm.filenameEmbdWeight);
      }
      if (this.parserConfigForm.taskPageSize !== null && this.parserConfigForm.taskPageSize !== undefined) {
        config.task_page_size = Number(this.parserConfigForm.taskPageSize);
      }
      if (this.raptorKnown || this.parserConfigForm.raptor.useRaptor) {
        const raptor = {
          use_raptor: Boolean(this.parserConfigForm.raptor.useRaptor)
        };
        if (this.parserConfigForm.raptor.maxToken !== null && this.parserConfigForm.raptor.maxToken !== undefined) {
          raptor.max_token = Number(this.parserConfigForm.raptor.maxToken);
        }
        if (this.parserConfigForm.raptor.threshold !== null && this.parserConfigForm.raptor.threshold !== undefined) {
          raptor.threshold = Number(this.parserConfigForm.raptor.threshold);
        }
        if (this.parserConfigForm.raptor.maxCluster !== null && this.parserConfigForm.raptor.maxCluster !== undefined) {
          raptor.max_cluster = Number(this.parserConfigForm.raptor.maxCluster);
        }
        if (this.parserConfigForm.raptor.randomSeed !== null && this.parserConfigForm.raptor.randomSeed !== undefined) {
          raptor.random_seed = Number(this.parserConfigForm.raptor.randomSeed);
        }
        if (this.parserConfigForm.raptor.prompt) {
          raptor.prompt = this.parserConfigForm.raptor.prompt;
        }
        config.raptor = raptor;
      }
      if (this.graphRagKnown || this.parserConfigForm.graphRag.useGraphRag) {
        config.graphrag = {
          use_graphrag: Boolean(this.parserConfigForm.graphRag.useGraphRag),
          entity_types: this.splitList(this.parserConfigForm.graphRag.entityTypes),
          method: this.parserConfigForm.graphRag.method || "light",
          community: Boolean(this.parserConfigForm.graphRag.community),
          resolution: Boolean(this.parserConfigForm.graphRag.resolution)
        };
      }
      return config;
    },
    splitList(value) {
      if (!value) {
        return [];
      }
      return value.split(",").map(item => item.trim()).filter(Boolean);
    },
    pruneEmptyFields(payload) {
      const result = { ...payload };
      ["avatar", "embeddingModel"].forEach(key => {
        if (result[key] === "") {
          delete result[key];
        }
      });
      return result;
    },
    formatDelimiterForInput(value) {
      return value.replace(/\r/g, "\\r").replace(/\n/g, "\\n").replace(/\t/g, "\\t");
    },
    parseDelimiterForPayload(value) {
      return value.replace(/\\r/g, "\r").replace(/\\n/g, "\n").replace(/\\t/g, "\t");
    },
    loadRAGModels() {
      if (this.ragModels.length > 0) {
        return;
      }

      Api.model.getRAGModels((res) => {
        if (res.data && res.data.code === 0) {
          this.ragModels = res.data.data || [];
          if (!this.form.id && !this.form.ragModelId && this.ragModels.length > 0) {
            this.$set(this.form, "ragModelId", this.ragModels[0].id);
          }
        } else {
          this.$message.error(this.$t("knowledgeBaseDialog.loadRAGModelsFailed"));
        }
      });
    }
  }
};
</script>

<style lang="scss" scoped>
.knowledge-base-dialog {
  ::v-deep .el-dialog {
    border-radius: 12px;
    overflow: hidden;
  }

  ::v-deep .el-dialog__body {
    max-height: 72vh;
    overflow-y: auto;
    padding: 20px 28px 8px;
  }

  ::v-deep .el-form-item {
    margin-bottom: 16px;
  }

  ::v-deep .el-form-item__label {
    font-weight: 500;
    color: #2f3442;
  }

  ::v-deep .el-input-number,
  ::v-deep .el-select {
    width: 100%;
  }

  .config-section {
    padding: 2px 0 18px;
    border-bottom: 1px solid #edf0f6;

    & + .config-section {
      padding-top: 18px;
    }

    &:last-of-type {
      border-bottom: 0;
    }
  }

  .section-title {
    margin: 0 0 14px;
    color: #1f2633;
    font-size: 15px;
    font-weight: 700;
  }

  .section-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    column-gap: 18px;
    align-items: start;
  }

  .section-grid-basic {
    grid-template-columns: minmax(0, 1fr) minmax(220px, 280px);
  }

  .grid-span-2 {
    grid-column: 1 / -1;
  }

  .advanced-collapse {
    border-top: 1px solid #edf0f6;
    border-bottom: 0;

    ::v-deep .el-collapse-item__header {
      font-size: 14px;
      font-weight: 600;
      color: #2f3442;
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
}

@media (max-width: 860px) {
  .knowledge-base-dialog {
    .section-grid,
    .section-grid-basic {
      grid-template-columns: 1fr;
    }
  }
}
</style>
