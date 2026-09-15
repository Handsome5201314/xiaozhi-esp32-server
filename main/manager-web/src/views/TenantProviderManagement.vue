<template>
  <div class="tenant-providers">
    <HeaderBar />
    <div class="page-body">
      <div class="toolbar"><h2>我的 Provider / Hermes</h2><el-button type="primary" @click="open()">新增配置</el-button></div>
      <el-alert type="info" :closable="false" show-icon
        title="密钥只提交到 Server，列表和接口永远只显示掩码或引用。管理员策略仍可限制地址和类型。" />
      <el-table :data="profiles" v-loading="loading" style="margin-top: 18px">
        <el-table-column prop="displayName" label="名称" />
        <el-table-column prop="capability" label="能力" width="100" />
        <el-table-column prop="providerType" label="类型" width="140" />
        <el-table-column prop="baseUrl" label="Server 地址" />
        <el-table-column prop="secretRef" label="密钥" width="150">
          <template slot-scope="scope"><span>{{ scope.row.secretRef ? '已配置（不可读）' : '未配置' }}</span></template>
        </el-table-column>
        <el-table-column label="操作" width="230">
          <template slot-scope="scope"><el-button type="text" @click="open(scope.row)">编辑</el-button><el-button type="text" @click="putSecret(scope.row)">更新密钥</el-button><el-button type="text" @click="remove(scope.row)">删除</el-button></template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog :title="form.id ? '编辑配置' : '新增配置'" :visible.sync="visible" width="520px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称"><el-input v-model="form.displayName" /></el-form-item>
        <el-form-item label="能力"><el-select v-model="form.capability"><el-option label="LLM" value="llm" /><el-option label="ASR" value="asr" /><el-option label="TTS" value="tts" /><el-option label="VLLM" value="vllm" /><el-option label="Hermes" value="hermes" /></el-select></el-form-item>
        <el-form-item label="Provider 类型"><el-input v-model="form.providerType" /></el-form-item>
        <el-form-item label="HTTPS 地址"><el-input v-model="form.baseUrl" /></el-form-item>
        <el-form-item label="模型名称"><el-input v-model="form.modelName" /></el-form-item>
        <el-form-item label="优先级"><el-input-number v-model="form.priority" :min="0" :max="9999" /></el-form-item>
      </el-form>
      <span slot="footer"><el-button @click="visible = false">取消</el-button><el-button type="primary" @click="save">保存</el-button></span>
    </el-dialog>
  </div>
</template>

<script>
import Api from '@/apis/api'
import HeaderBar from '@/components/HeaderBar.vue'
export default {
  components: { HeaderBar },
  data () { return { profiles: [], loading: false, visible: false, form: {} } },
  created () { this.load() },
  methods: {
    load () { this.loading = true; Api.tenantProvider.list(res => { this.loading = false; if (res.data && res.data.code === 0) this.profiles = res.data.data || [] }) },
    open (row) { this.form = Object.assign({ capability: 'llm', providerType: 'openai', priority: 100, isEnabled: 1 }, row || {}); this.visible = true },
    save () { Api.tenantProvider.save(this.form, res => { if (res.data && res.data.code === 0) { this.visible = false; this.load() } else this.$message.error((res.data && res.data.msg) || '保存失败') }) },
    putSecret (row) { this.$prompt('输入新密钥，保存后不会再次显示原文', '更新密钥', { inputType: 'password' }).then(({ value }) => Api.tenantProvider.putSecret(row.id, value, res => { if (res.data && res.data.code === 0) { this.$message.success('密钥已更新'); this.load() } else this.$message.error('密钥更新失败') })).catch(() => {}) },
    remove (row) { this.$confirm('删除该 Provider 配置？', '确认').then(() => Api.tenantProvider.remove(row.id, () => this.load())).catch(() => {}) }
  }
}
</script>

<style scoped>
.page-body { padding: 28px 38px; }
.toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.toolbar h2 { margin: 0; }
</style>
