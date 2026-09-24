<template>
  <div class="tenant-providers">
    <HeaderBar />
    <div class="page-body">
      <div class="toolbar"><h2>我的 Provider / Hermes</h2><span><el-button @click="openProvider">新增 Provider</el-button><el-button type="primary" @click="openHermes">新增 Hermes</el-button></span></div>
      <el-alert type="info" :closable="false" show-icon title="Hermes 由用户独立部署并提供 HTTPS 地址；密钥只提交到 Server，列表永远不显示原文。" />
      <h3>Hermes 实例</h3>
      <el-table :data="hermes" v-loading="loadingHermes" style="margin-top: 12px">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="baseUrl" label="HTTPS 地址" />
        <el-table-column prop="model" label="模型" />
        <el-table-column prop="deviceId" label="设备绑定" />
        <el-table-column prop="priority" label="优先级" width="90" />
        <el-table-column label="密钥" width="120"><template slot-scope="scope">{{ scope.row.secretRef ? '已配置（不可读）' : '未配置' }}</template></el-table-column>
        <el-table-column label="操作" width="240"><template slot-scope="scope"><el-button type="text" @click="openHermes(scope.row)">编辑</el-button><el-button type="text" @click="putHermesSecret(scope.row)">更新密钥</el-button><el-button type="text" @click="removeHermes(scope.row)">删除</el-button></template></el-table-column>
      </el-table>
      <h3>普通 Provider</h3>
      <el-table :data="profiles" v-loading="loadingProfiles" style="margin-top: 12px">
        <el-table-column prop="displayName" label="名称" />
        <el-table-column prop="capability" label="能力" width="100" />
        <el-table-column prop="providerType" label="类型" width="140" />
        <el-table-column prop="baseUrl" label="地址" />
        <el-table-column prop="secretRef" label="密钥" width="150"><template slot-scope="scope">{{ scope.row.secretRef ? '已配置（不可读）' : '未配置' }}</template></el-table-column>
        <el-table-column label="操作" width="230"><template slot-scope="scope"><el-button type="text" @click="openProvider(scope.row)">编辑</el-button><el-button type="text" @click="putProviderSecret(scope.row)">更新密钥</el-button><el-button type="text" @click="removeProvider(scope.row)">删除</el-button></template></el-table-column>
      </el-table>
    </div>
    <el-dialog :title="formMode === 'hermes' ? (form.id ? '编辑 Hermes' : '新增 Hermes') : (form.id ? '编辑 Provider' : '新增 Provider')" :visible.sync="visible" width="560px">
      <el-form :model="form" label-width="110px">
        <template v-if="formMode === 'hermes'">
          <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
          <el-form-item label="HTTPS 地址"><el-input v-model="form.baseUrl" /></el-form-item>
          <el-form-item label="模型名称"><el-input v-model="form.model" /></el-form-item>
          <el-form-item label="能力 JSON"><el-input v-model="form.capabilities" placeholder='例如 ["chat","summary"]' /></el-form-item>
          <el-form-item label="设备 ID（可选）"><el-input v-model="form.deviceId" /></el-form-item>
          <el-form-item label="优先级"><el-input-number v-model="form.priority" :min="0" :max="9999" /></el-form-item>
          <el-form-item label="启用"><el-switch v-model="form.isEnabled" :active-value="1" :inactive-value="0" /></el-form-item>
        </template>
        <template v-else>
          <el-form-item label="名称"><el-input v-model="form.displayName" /></el-form-item>
          <el-form-item label="能力"><el-select v-model="form.capability"><el-option label="LLM" value="llm" /><el-option label="ASR" value="asr" /><el-option label="TTS" value="tts" /><el-option label="VLLM" value="vllm" /></el-select></el-form-item>
          <el-form-item label="Provider 类型"><el-input v-model="form.providerType" /></el-form-item>
          <el-form-item label="HTTPS 地址"><el-input v-model="form.baseUrl" /></el-form-item>
          <el-form-item label="模型名称"><el-input v-model="form.modelName" /></el-form-item>
          <el-form-item label="优先级"><el-input-number v-model="form.priority" :min="0" :max="9999" /></el-form-item>
        </template>
      </el-form>
      <span slot="footer"><el-button @click="visible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></span>
    </el-dialog>
  </div>
</template>

<script>
import Api from '@/apis/api'
import HeaderBar from '@/components/HeaderBar.vue'
export default {
  components: { HeaderBar },
  data () { return { profiles: [], hermes: [], loadingProfiles: false, loadingHermes: false, saving: false, visible: false, formMode: 'provider', form: {} } },
  created () { this.load() },
  methods: {
    load () {
      this.loadingProfiles = true; this.loadingHermes = true
      Api.tenantProvider.list(res => { this.loadingProfiles = false; if (res.data && res.data.code === 0) this.profiles = res.data.data || [] })
      Api.tenantProvider.hermesList(res => { this.loadingHermes = false; if (res.data && res.data.code === 0) this.hermes = res.data.data || [] })
    },
    openProvider (row) { this.formMode = 'provider'; this.form = Object.assign({ capability: 'llm', providerType: 'openai', priority: 100, isEnabled: 1 }, row || {}); this.visible = true },
    openHermes (row) { this.formMode = 'hermes'; this.form = Object.assign({ name: '', baseUrl: '', model: '', capabilities: '["chat"]', priority: 100, isEnabled: 1 }, row || {}); this.visible = true },
    save () {
      this.saving = true
      const done = res => { this.saving = false; if (res.data && res.data.code === 0) { this.visible = false; this.load() } else this.$message.error((res.data && res.data.msg) || '保存失败') }
      const failed = res => {
        this.saving = false
        this.$message.error((res && res.data && res.data.msg) || '保存失败')
      }
      if (this.formMode === 'hermes') Api.tenantProvider.hermesSave(this.form, done, failed); else Api.tenantProvider.save(this.form, done)
    },
    putProviderSecret (row) { this.$prompt('输入新密钥，保存后不会再次显示原文', '更新密钥', { inputType: 'password' }).then(({ value }) => Api.tenantProvider.putSecret(row.id, value, res => { if (res.data && res.data.code === 0) { this.$message.success('密钥已更新'); this.load() } else this.$message.error('密钥更新失败') })).catch(() => {}) },
    putHermesSecret (row) { this.$prompt('输入 Hermes API Key，保存后不会再次显示原文', '更新密钥', { inputType: 'password' }).then(({ value }) => Api.tenantProvider.hermesPutSecret(row.id, value, res => { if (res.data && res.data.code === 0) { this.$message.success('密钥已更新'); this.load() } else this.$message.error('密钥更新失败') })).catch(() => {}) },
    removeProvider (row) { this.$confirm('删除该 Provider 配置？', '确认').then(() => Api.tenantProvider.remove(row.id, () => this.load())).catch(() => {}) },
    removeHermes (row) { this.$confirm('删除该 Hermes 实例？', '确认').then(() => Api.tenantProvider.hermesRemove(row.id, () => this.load())).catch(() => {}) }
  }
}
</script>

<style scoped>
.page-body { padding: 28px 38px; }
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.toolbar h2 { margin: 0; }
h3 { margin: 28px 0 0; }
</style>
