<template>
  <section class="exhibit-center" aria-labelledby="exhibit-center-title">
    <div class="center-heading">
      <div>
        <h2 id="exhibit-center-title">展品内容中心</h2>
        <p>维护游客端展示内容，并用展品 ID 关联知识库资料。</p>
      </div>
      <el-button type="primary" icon="el-icon-plus" @click="openCreate">新建展品</el-button>
    </div>

    <div class="status-summary" aria-label="展品状态概览">
      <button v-for="item in statusOptions" :key="item.value" type="button" :class="{ active: filters.status === item.value }" @click="selectStatus(item.value)">
        <span>{{ item.label }}</span><strong v-if="filters.status === item.value">{{ total }}</strong>
      </button>
    </div>

    <div class="content-toolbar">
      <el-input v-model="filters.keyword" clearable prefix-icon="el-icon-search" placeholder="搜索展品、展览或类别" aria-label="搜索展品" @keyup.enter.native="load" />
      <el-select v-model="filters.status" clearable placeholder="全部状态" aria-label="按发布状态筛选" @change="load">
        <el-option v-for="item in statusOptions.slice(1)" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-button icon="el-icon-refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="items" stripe empty-text="还没有展品，先新建一件吧">
      <el-table-column label="展品" min-width="250">
        <template slot-scope="scope">
          <div class="exhibit-identity">
            <img v-if="scope.row.imageUrl" :src="scope.row.imageUrl" :alt="scope.row.name" />
            <span v-else class="image-placeholder"><i class="el-icon-picture-outline"></i></span>
            <div><strong>{{ scope.row.name }}</strong><small>{{ scope.row.id }}</small></div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="exhibition" label="展览" min-width="170" show-overflow-tooltip />
      <el-table-column label="年代 / 类别" min-width="150">
        <template slot-scope="scope"><span>{{ scope.row.era }}</span><small class="secondary">{{ scope.row.category }}</small></template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template slot-scope="scope"><el-tag size="small" :type="statusType(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column label="更新时间" width="165">
        <template slot-scope="scope">{{ formatDate(scope.row.updateDate) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template slot-scope="scope">
          <el-button v-if="scope.row.status !== 'PUBLISHED'" type="text" @click="openEdit(scope.row)">编辑</el-button>
          <el-button v-if="scope.row.status !== 'PUBLISHED'" type="text" @click="changeStatus(scope.row, 'PUBLISHED')">发布</el-button>
          <el-button v-else type="text" @click="changeStatus(scope.row, 'OFFLINE')">下线</el-button>
          <el-button type="text" @click="openKnowledge(scope.row)">关联资料</el-button>
          <el-button v-if="scope.row.status !== 'PUBLISHED'" class="danger-link" type="text" @click="remove(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination class="pagination" background layout="total, prev, pager, next" :total="total" :page-size="filters.limit" :current-page="filters.page" @current-change="changePage" />

    <el-dialog :title="form.id ? '编辑展品' : '新建展品草稿'" :visible.sync="dialogVisible" width="760px" :close-on-click-modal="false" append-to-body>
      <el-form ref="form" :model="form" :rules="rules" label-position="top" class="exhibit-form">
        <div class="form-grid">
          <el-form-item label="博物馆" prop="museum"><el-input v-model="form.museum" maxlength="120" /></el-form-item>
          <el-form-item label="所属展览"><el-input v-model="form.exhibition" maxlength="120" /></el-form-item>
          <el-form-item label="展品名称" prop="name"><el-input v-model="form.name" maxlength="120" show-word-limit /></el-form-item>
          <el-form-item label="年代" prop="era"><el-input v-model="form.era" maxlength="80" /></el-form-item>
          <el-form-item label="材质" prop="material"><el-input v-model="form.material" maxlength="120" /></el-form-item>
          <el-form-item label="类别" prop="category"><el-input v-model="form.category" maxlength="80" /></el-form-item>
        </div>
        <el-form-item label="游客端摘要" prop="summary"><el-input v-model="form.summary" type="textarea" :rows="3" maxlength="1200" show-word-limit /></el-form-item>
        <div class="image-sort-grid">
          <el-form-item label="展品主图">
            <div class="image-editor">
              <div class="image-preview" :class="{ empty: !form.imageUrl }">
                <img v-if="form.imageUrl" :src="form.imageUrl" :alt="form.name || '展品图片预览'" />
                <div v-else><i class="el-icon-picture-outline"></i><span>上传后在游客端展示</span></div>
              </div>
              <div class="image-actions">
                <el-upload action="#" accept="image/jpeg,image/png,image/webp" :show-file-list="false" :http-request="uploadImage" :before-upload="validateImage">
                  <el-button size="small" type="primary" plain :loading="imageUploading" icon="el-icon-upload2">{{ form.imageUrl ? '替换图片' : '上传图片' }}</el-button>
                </el-upload>
                <el-button v-if="form.imageUrl" size="small" type="text" @click="clearImage">移除</el-button>
                <small>JPG、PNG 或 WebP，最大 8 MB</small>
              </div>
            </div>
            <el-input v-model="form.imageUrl" class="image-url-input" size="small" placeholder="也可以粘贴 HTTPS 图片地址" aria-label="公开图片地址" @input="clearImageHash" />
          </el-form-item>
          <el-form-item label="展示排序"><el-input-number v-model="form.sort" :min="0" :max="9999" controls-position="right" /></el-form-item>
        </div>
        <el-form-item label="主题标签"><el-input v-model="tagText" placeholder="使用中文逗号分隔，如：马王堆精选，汉代生活" /></el-form-item>

        <div class="array-section">
          <div class="array-heading"><div><strong>观察提示</strong><span>帮助游客知道先看哪里</span></div><el-button size="mini" icon="el-icon-plus" @click="form.observations.push(emptyObservation())">添加</el-button></div>
          <div v-for="(item, index) in form.observations" :key="`observation-${index}`" class="array-row two-columns">
            <el-input v-model="item.title" placeholder="观察标题" /><el-input v-model="item.detail" placeholder="具体提示" />
            <el-button type="text" aria-label="删除观察提示" @click="form.observations.splice(index, 1)"><i class="el-icon-delete"></i></el-button>
          </div>
        </div>

        <div class="array-section">
          <div class="array-heading"><div><strong>公开资料来源</strong><span>发布前至少填写一条</span></div><el-button size="mini" icon="el-icon-plus" @click="form.sources.push(emptySource())">添加</el-button></div>
          <div v-for="(item, index) in form.sources" :key="`source-${index}`" class="source-editor">
            <div class="array-row source-columns"><el-input v-model="item.title" placeholder="资料名称" /><el-input v-model="item.page" placeholder="页码（可选）" /><el-select v-model="item.status"><el-option label="已核验" value="verified" /><el-option label="解释性内容" value="interpretation" /></el-select><el-button type="text" aria-label="删除资料来源" @click="form.sources.splice(index, 1)"><i class="el-icon-delete"></i></el-button></div>
            <el-input v-model="item.excerpt" type="textarea" :rows="2" placeholder="游客可见的资料摘录" />
          </div>
        </div>
      </el-form>
      <span slot="footer"><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存草稿</el-button></span>
    </el-dialog>
  </section>
</template>

<script>
import Api from '@/apis/api';

const freshForm = () => ({ id: '', museum: '湖南省博物馆', exhibition: '长沙马王堆汉墓陈列', name: '', era: '', material: '', category: '', summary: '', imageUrl: '', imageSha256: '', tags: [], observations: [], sources: [], sort: 0 });

export default {
  name: 'MuseumExhibitCenter',
  data() {
    return {
      loading: false, saving: false, imageUploading: false, dialogVisible: false, items: [], total: 0, tagText: '',
      filters: { page: 1, limit: 10, keyword: '', status: '' },
      form: freshForm(),
      statusOptions: [{ label: '全部', value: '' }, { label: '草稿', value: 'DRAFT' }, { label: '已发布', value: 'PUBLISHED' }, { label: '已下线', value: 'OFFLINE' }],
      rules: {
        museum: [{ required: true, message: '请输入博物馆名称', trigger: 'blur' }], name: [{ required: true, message: '请输入展品名称', trigger: 'blur' }],
        era: [{ required: true, message: '请输入年代', trigger: 'blur' }], material: [{ required: true, message: '请输入材质', trigger: 'blur' }],
        category: [{ required: true, message: '请输入类别', trigger: 'blur' }], summary: [{ required: true, message: '请输入游客端摘要', trigger: 'blur' }]
      }
    };
  },
  created() { this.load(); },
  methods: {
    emptyObservation() { return { title: '', detail: '' }; },
    emptySource() { return { title: '', page: '', excerpt: '', status: 'verified' }; },
    validateImage(file) {
      const supported = ['image/jpeg', 'image/png', 'image/webp'].includes(file.type);
      if (!supported) this.$message.error('仅支持 JPG、PNG 或 WebP 图片');
      if (file.size > 8 * 1024 * 1024) this.$message.error('展品图片不能超过 8 MB');
      return supported && file.size <= 8 * 1024 * 1024;
    },
    uploadImage({ file, onSuccess, onError }) {
      this.imageUploading = true;
      Api.museumExhibit.uploadImage(file, ({ data }) => {
        const result = data.data || {};
        this.form.imageUrl = result.imageUrl || '';
        this.form.imageSha256 = result.imageSha256 || '';
        this.imageUploading = false;
        this.$message.success('展品图片已上传');
        onSuccess(result);
      }, (error) => {
        this.imageUploading = false;
        onError(error);
      });
    },
    clearImage() { this.form.imageUrl = ''; this.form.imageSha256 = ''; },
    clearImageHash() { this.form.imageSha256 = ''; },
    load() {
      this.loading = true;
      Api.museumExhibit.list(this.filters, ({ data }) => { this.items = (data.data && data.data.list) || []; this.total = Number((data.data && data.data.total) || 0); this.loading = false; }, () => { this.loading = false; });
    },
    openCreate() { this.form = freshForm(); this.tagText = ''; this.dialogVisible = true; this.$nextTick(() => this.$refs.form && this.$refs.form.clearValidate()); },
    openEdit(row) { this.form = JSON.parse(JSON.stringify(row)); this.form.observations = this.form.observations || []; this.form.sources = this.form.sources || []; this.tagText = (this.form.tags || []).join('，'); this.dialogVisible = true; },
    save() {
      this.$refs.form.validate((valid) => {
        if (!valid) return;
        this.saving = true;
        const payload = { ...this.form, tags: this.tagText.split(/[，,]/).map(item => item.trim()).filter(Boolean), observations: this.form.observations.filter(item => item.title && item.detail), sources: this.form.sources.filter(item => item.title && item.excerpt) };
        const done = () => { this.saving = false; this.dialogVisible = false; this.$message.success('展品草稿已保存'); this.load(); };
        const fail = () => { this.saving = false; };
        if (payload.id) Api.museumExhibit.update(payload.id, payload, done, fail); else Api.museumExhibit.create(payload, done, fail);
      });
    },
    changeStatus(row, status) {
      const action = status === 'PUBLISHED' ? '发布' : '下线';
      this.$confirm(`确定${action}“${row.name}”吗？`, `${action}展品`, { type: status === 'PUBLISHED' ? 'success' : 'warning' }).then(() => {
        Api.museumExhibit.changeStatus(row.id, status, () => { this.$message.success(`展品已${action}`); this.load(); });
      }).catch(() => {});
    },
    remove(row) {
      this.$confirm(`删除“${row.name}”后无法恢复，确定继续吗？`, '删除展品', { type: 'warning' }).then(() => {
        Api.museumExhibit.remove(row.id, () => { this.$message.success('展品已删除'); this.load(); });
      }).catch(() => {});
    },
    openKnowledge(row) { this.$emit('open-knowledge', row); },
    selectStatus(status) { this.filters.status = status; this.filters.page = 1; this.load(); },
    changePage(page) { this.filters.page = page; this.load(); },
    statusLabel(status) { return ({ DRAFT: '草稿', PUBLISHED: '已发布', OFFLINE: '已下线' })[status] || status; },
    statusType(status) { return ({ DRAFT: 'info', PUBLISHED: 'success', OFFLINE: 'warning' })[status] || 'info'; },
    formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—'; }
  }
};
</script>

<style scoped lang="scss">
.exhibit-center { color: #263238; }
.center-heading, .content-toolbar, .array-heading { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.center-heading h2 { margin: 0 0 8px; font-size: 22px; }
.center-heading p, .array-heading span { margin: 0; color: #718096; font-size: 13px; }
.status-summary { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 22px 0 18px; }
.status-summary button { display: flex; align-items: center; justify-content: space-between; padding: 16px; color: #566375; background: #f7f9fc; border: 1px solid #e5eaf1; border-radius: 12px; cursor: pointer; }
.status-summary button.active { color: #356f65; background: #edf8f5; border-color: #8dc4b7; box-shadow: 0 6px 18px rgba(65, 126, 113, .1); }
.status-summary strong { font-size: 21px; }
.content-toolbar { justify-content: flex-start; margin-bottom: 16px; }
.content-toolbar .el-input { width: 320px; }
.content-toolbar .el-select { width: 150px; }
.exhibit-identity { display: flex; align-items: center; gap: 12px; }
.exhibit-identity img, .image-placeholder { width: 50px; height: 50px; flex: 0 0 auto; object-fit: cover; border-radius: 10px; }
.image-placeholder { display: grid; place-items: center; color: #91a0b4; background: #eef2f7; font-size: 20px; }
.exhibit-identity strong, .exhibit-identity small, .secondary { display: block; }
.exhibit-identity small, .secondary { margin-top: 4px; color: #8a96a8; font-size: 12px; }
.danger-link { color: #d45b5b; }
.pagination { margin-top: 20px; text-align: right; }
.form-grid, .image-sort-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 18px; }
.image-sort-grid { grid-template-columns: minmax(0, 1fr) 160px; }
.image-editor { display: flex; align-items: center; gap: 14px; }
.image-preview { width: 112px; height: 84px; flex: 0 0 auto; overflow: hidden; border: 1px solid #d9e2ec; border-radius: 12px; background: #f5f7fa; }
.image-preview img { width: 100%; height: 100%; object-fit: cover; }
.image-preview.empty { display: grid; place-items: center; color: #8a96a8; border-style: dashed; }
.image-preview.empty div { display: grid; justify-items: center; gap: 5px; padding: 8px; text-align: center; font-size: 11px; line-height: 1.35; }
.image-preview.empty i { color: #5b897e; font-size: 24px; }
.image-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; }
.image-actions small { width: 100%; color: #8a96a8; font-size: 12px; }
.image-url-input { margin-top: 10px; }
.array-section { margin-top: 18px; padding: 16px; background: #f7f9fc; border: 1px solid #e8edf3; border-radius: 12px; }
.array-heading { margin-bottom: 12px; }
.array-heading span { display: block; margin-top: 3px; }
.array-row { display: grid; align-items: center; gap: 8px; margin-top: 8px; }
.two-columns { grid-template-columns: 180px minmax(0, 1fr) 34px; }
.source-columns { grid-template-columns: minmax(0, 1fr) 105px 125px 34px; }
.source-editor + .source-editor { margin-top: 14px; padding-top: 14px; border-top: 1px solid #e1e7ef; }
@media (max-width: 760px) { .status-summary { grid-template-columns: repeat(2, 1fr); } .content-toolbar { align-items: stretch; flex-direction: column; } .content-toolbar .el-input, .content-toolbar .el-select { width: 100%; } .form-grid, .image-sort-grid { grid-template-columns: 1fr; } .two-columns, .source-columns { grid-template-columns: 1fr; } }
</style>
