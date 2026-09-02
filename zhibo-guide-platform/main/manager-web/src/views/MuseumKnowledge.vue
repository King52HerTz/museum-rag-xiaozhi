<template>
  <div class="museum-knowledge-page">
    <HeaderBar />
    <main class="museum-main">
      <section class="hero-card">
        <div class="hero-copy">
          <div class="eyebrow">知识资产中心</div>
          <h1>湖南省博物馆知识库</h1>
          <p>
            统一维护权威资料、跟踪索引状态并验证检索效果。这里的资料将作为智博导览回答文物与展览问题时的事实依据。
          </p>
          <div class="hero-actions">
            <el-button type="primary" icon="el-icon-upload2" @click="activateUpload">
              上传资料
            </el-button>
            <el-button icon="el-icon-setting" :loading="workbenchLoading" @click="openWorkbench">
              高级工作台
            </el-button>
          </div>
          <el-alert v-if="workbenchMessage" class="workbench-message" :title="workbenchMessage" type="info" :closable="false" />
        </div>
        <div class="hero-visual" aria-hidden="true">
          <img src="@/assets/brand/museum-hero.jpg" alt="" />
        </div>
      </section>

      <section class="summary-grid" aria-label="知识库概览">
        <article class="summary-card">
          <span class="summary-label">资料总数</span>
          <strong>{{ documents.length }}</strong>
          <small>份权威资料</small>
        </article>
        <article class="summary-card">
          <span class="summary-label">检索分块</span>
          <strong>{{ totalChunks }}</strong>
          <small>个可检索片段</small>
        </article>
        <article class="summary-card">
          <span class="summary-label">知识范围</span>
          <strong class="summary-scope">马王堆汉墓</strong>
          <small>{{ exhibitionOptions.length || 1 }} 个展览范围</small>
        </article>
        <article class="summary-card" :class="{ 'summary-card-error': documentLoadFailed }">
          <span class="summary-label">RAG 服务</span>
          <strong class="summary-status">
            <i :class="documentLoadFailed ? 'el-icon-warning-outline' : 'el-icon-circle-check'"></i>
            {{ documentLoadFailed ? '连接异常' : '运行正常' }}
          </strong>
          <small>{{ documentLoadFailed ? '请检查稳定版服务' : '资料列表已同步' }}</small>
        </article>
      </section>

      <section class="workspace-card">
        <el-tabs v-model="activeWorkspace" class="workspace-tabs">
          <el-tab-pane name="documents">
            <span slot="label"><i class="el-icon-folder-opened"></i> 资料管理</span>

            <div class="section-heading documents-heading">
              <div>
                <h2>知识库资料</h2>
                <p>维护用于导览问答的来源文件。上传完成后，系统会自动解析、分块并建立索引。</p>
              </div>
              <div class="document-actions">
                <el-button icon="el-icon-refresh" :loading="documentsLoading" @click="loadDocuments">刷新</el-button>
                <el-upload
                  ref="documentUpload"
                  action="#"
                  :auto-upload="false"
                  :show-file-list="false"
                  :limit="1"
                  accept=".pdf,.doc,.docx,.xls,.xlsx"
                  :on-change="handleDocumentChange"
                  :on-exceed="handleUploadExceed"
                >
                  <el-button ref="uploadButton" type="primary" icon="el-icon-upload2" :loading="uploadLoading">
                    上传资料
                  </el-button>
                </el-upload>
              </div>
            </div>

            <el-alert
              v-if="uploadMessage"
              class="document-alert"
              :title="uploadMessage"
              :type="uploadStatus === 'failed' ? 'error' : uploadStatus === 'completed' ? 'success' : 'info'"
              :closable="false"
              show-icon
            />

            <div v-if="uploadLoading" class="upload-progress">
              <div class="upload-progress-title">
                <span>{{ uploadFilename || '正在处理资料' }}</span>
                <span>{{ uploadProgress }}%</span>
              </div>
              <el-progress :percentage="uploadProgress" :status="uploadStatus === 'failed' ? 'exception' : undefined" />
              <p>{{ uploadMessage || '正在提交上传任务...' }}</p>
            </div>

            <div class="document-toolbar">
              <el-input
                v-model="documentKeyword"
                clearable
                prefix-icon="el-icon-search"
                placeholder="搜索文件名称"
                aria-label="搜索文件名称"
              />
              <el-select v-model="documentExhibition" clearable placeholder="全部展览" aria-label="按展览筛选">
                <el-option v-for="item in exhibitionOptions" :key="item" :label="item" :value="item" />
              </el-select>
              <span class="document-count">显示 {{ filteredDocuments.length }} / {{ documents.length }} 份资料</span>
            </div>

            <el-table
              v-loading="documentsLoading"
              :data="filteredDocuments"
              stripe
              class="document-table"
              empty-text="暂无符合条件的资料"
            >
              <el-table-column prop="filename" label="资料名称" min-width="280">
                <template slot-scope="scope">
                  <div class="document-name">
                    <span class="file-icon"><i class="el-icon-document"></i></span>
                    <div>
                      <strong>{{ scope.row.filename }}</strong>
                      <small>{{ (scope.row.file_type || '文件').toUpperCase() }}</small>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="所属范围" min-width="240">
                <template slot-scope="scope">
                  <div class="document-profile">
                    <strong>{{ scope.row.exhibition || queryForm.exhibition }}</strong>
                    <span>{{ scope.row.museum || queryForm.museum }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="chunk_count" label="分块数量" width="110" align="center" />
              <el-table-column label="状态" width="110" align="center">
                <template>
                  <span class="status-badge"><i class="el-icon-circle-check"></i> 可检索</span>
                </template>
              </el-table-column>
              <el-table-column prop="uploaded_at" label="更新时间" width="170">
                <template slot-scope="scope">{{ formatDate(scope.row.uploaded_at) }}</template>
              </el-table-column>
              <el-table-column label="操作" width="90" fixed="right" align="center">
                <template slot-scope="scope">
                  <el-button
                    type="text"
                    class="delete-document-button"
                    :loading="deletingFilename === scope.row.filename"
                    @click="deleteDocument(scope.row)"
                  >删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane name="retrieval">
            <span slot="label"><i class="el-icon-search"></i> 检索测试</span>

            <div class="retrieval-layout">
              <div class="query-card">
                <div class="section-heading">
                  <div>
                    <h2>验证资料召回效果</h2>
                    <p>输入游客可能提出的问题，确认系统能否找到正确、可靠的资料片段。</p>
                  </div>
                </div>

                <el-form :model="queryForm" label-position="top" class="query-form">
                  <el-form-item label="检索问题">
                    <el-input
                      v-model="queryForm.question"
                      type="textarea"
                      :rows="4"
                      maxlength="300"
                      show-word-limit
                      placeholder="例如：黑地彩绘棺的尺寸和装饰有什么特点？"
                      @keyup.ctrl.enter.native="runQuery"
                    />
                  </el-form-item>
                  <div class="question-suggestions">
                    <span>试试示例：</span>
                    <button v-for="item in sampleQuestions" :key="item" type="button" @click="queryForm.question = item">
                      {{ item }}
                    </button>
                  </div>
                  <button class="advanced-toggle" type="button" @click="showAdvanced = !showAdvanced">
                    <i :class="showAdvanced ? 'el-icon-arrow-up' : 'el-icon-arrow-down'"></i>
                    {{ showAdvanced ? '收起检索范围' : '设置检索范围' }}
                  </button>
                  <div v-show="showAdvanced" class="form-grid">
                    <el-form-item label="博物馆">
                      <el-input v-model="queryForm.museum" clearable />
                    </el-form-item>
                    <el-form-item label="展览">
                      <el-input v-model="queryForm.exhibition" clearable />
                    </el-form-item>
                    <el-form-item label="返回片段数">
                      <el-input-number v-model="queryForm.top_k" :min="1" :max="10" controls-position="right" />
                    </el-form-item>
                  </div>
                  <div class="query-actions">
                    <el-button type="primary" icon="el-icon-search" :loading="queryLoading" @click="runQuery">
                      开始检索
                    </el-button>
                    <el-button v-if="queryResult" @click="clearResult">清空结果</el-button>
                  </div>
                </el-form>
              </div>

              <div class="result-card">
                <div class="section-heading result-heading">
                  <div>
                    <h2>召回结果</h2>
                    <p>结果按相关度排序，回答生成时会引用这些来源片段。</p>
                  </div>
                  <el-tag v-if="queryResult" :type="resultTagType" effect="plain">{{ resultLabel }}</el-tag>
                </div>

                <el-empty v-if="!queryResult && !queryLoading" description="输入问题后，这里将显示命中的权威资料片段。" />

                <div v-if="queryLoading" class="loading-box">
                  <i class="el-icon-loading"></i>
                  <div><strong>正在检索知识库</strong><span>正在匹配最相关的资料片段...</span></div>
                </div>

                <div v-if="queryResult && contexts.length === 0 && !queryLoading" class="empty-result">
                  <i :class="resultOk ? 'el-icon-search' : 'el-icon-warning-outline'"></i>
                  <div>
                    <strong>{{ resultOk ? '未找到直接相关的资料' : '检索服务暂时不可用' }}</strong>
                    <span>{{ resultOk ? '请确认资料已经完成解析，或尝试使用文物全称重新检索。' : '请检查稳定版 RAG 服务和桥接配置后重试。' }}</span>
                  </div>
                </div>

                <div v-if="contexts.length > 0" class="context-list">
                  <article v-for="item in contexts" :key="item.index || item.chunk_id || item.content" class="context-item">
                    <header class="context-header">
                      <span class="context-index">{{ item.index }}</span>
                      <div class="context-source">
                        <strong>{{ item.title || item.source || '未知来源' }}</strong>
                        <span>
                          <template v-if="item.page_number">第 {{ item.page_number }} 页</template>
                          <template v-if="formatScore(item)"> · 相关度 {{ formatScore(item) }}</template>
                        </span>
                      </div>
                      <el-tag size="mini" effect="plain">权威资料</el-tag>
                    </header>
                    <p>{{ item.content }}</p>
                  </article>
                </div>

                <details v-if="queryResult && queryResult.trace" class="trace-box">
                  <summary><i class="el-icon-setting"></i> 开发诊断信息</summary>
                  <p>仅用于排查检索链路，普通使用无需查看。</p>
                  <pre>{{ prettyTrace }}</pre>
                </details>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </section>
    </main>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import Api from "@/apis/api";

const SAMPLE_QUESTIONS = [
  "马王堆汉墓的素纱单衣为什么这么有名？",
  "黑地彩绘棺的尺寸和装饰有什么特点？",
  "T形帛画表现了怎样的汉代宇宙观？"
];

export default {
  name: "MuseumKnowledge",
  components: { HeaderBar },
  data: function () {
    return {
      workbenchUrl: (process.env.VUE_APP_MUSEUM_WORKBENCH_URL || "http://127.0.0.1:8000/").trim(),
      workbenchMessage: "",
      workbenchLoading: false,
      activeWorkspace: "documents",
      documents: [],
      documentsLoading: false,
      documentLoadFailed: false,
      documentKeyword: "",
      documentExhibition: "",
      uploadLoading: false,
      uploadFilename: "",
      uploadProgress: 0,
      uploadStatus: "",
      uploadMessage: "",
      deletingFilename: "",
      uploadPollTimer: null,
      deletePollTimer: null,
      queryLoading: false,
      queryResult: null,
      showAdvanced: false,
      sampleQuestions: SAMPLE_QUESTIONS,
      queryForm: {
        question: SAMPLE_QUESTIONS[0],
        museum: "湖南省博物馆",
        exhibition: "长沙马王堆汉墓陈列",
        top_k: 3,
        need_trace: true
      }
    };
  },
  created: function () {
    this.loadDocuments();
  },
  beforeDestroy: function () {
    this.stopUploadPolling();
    this.stopDeletePolling();
  },
  computed: {
    contexts: function () {
      return (this.queryResult && this.queryResult.contexts) || [];
    },
    totalChunks: function () {
      return this.documents.reduce((total, item) => total + Number(item.chunk_count || 0), 0);
    },
    exhibitionOptions: function () {
      return Array.from(new Set(this.documents.map((item) => item.exhibition).filter(Boolean))).sort();
    },
    filteredDocuments: function () {
      const keyword = this.documentKeyword.trim().toLowerCase();
      return this.documents.filter((item) => {
        const matchesKeyword = !keyword || String(item.filename || "").toLowerCase().includes(keyword);
        const matchesExhibition = !this.documentExhibition || item.exhibition === this.documentExhibition;
        return matchesKeyword && matchesExhibition;
      });
    },
    resultOk: function () {
      return this.queryResult && Number(this.queryResult.code) === 0;
    },
    resultLabel: function () {
      if (!this.queryResult) {
        return "";
      }
      if (!this.resultOk) {
        return "服务异常";
      }
      if (this.contexts.length === 0) {
        return "未命中资料";
      }
      return `命中 ${this.contexts.length} 个片段`;
    },
    resultTagType: function () {
      if (!this.resultOk) {
        return "danger";
      }
      return this.contexts.length > 0 ? "success" : "warning";
    },
    prettyTrace: function () {
      return JSON.stringify(this.queryResult.trace || {}, null, 2);
    }
  },
  methods: {
    unwrap: function (res) {
      if (res && res.data && res.data.data) {
        return res.data.data;
      }
      if (res && res.data) {
        return res.data;
      }
      return {};
    },
    loadDocuments: function () {
      this.documentsLoading = true;
      Api.museumRag.listDocuments(
        (res) => {
          const data = this.unwrap(res);
          this.documents = Array.isArray(data.documents) ? data.documents : [];
          this.documentLoadFailed = false;
          this.documentsLoading = false;
        },
        () => {
          this.documents = [];
          this.documentLoadFailed = true;
          this.documentsLoading = false;
          this.$message.error("获取博物馆知识库资料失败，请检查 RAG 服务是否启动。");
        }
      );
    },
    handleUploadExceed: function () {
      this.$message.warning("一次只能上传一个文件，请等待当前任务完成。");
    },
    handleDocumentChange: function (uploadFile) {
      const file = uploadFile && uploadFile.raw;
      if (!file) {
        return;
      }
      const filename = file.name || "";
      if (!/\.(pdf|docx?|xlsx?)$/i.test(filename)) {
        this.$message.warning("仅支持 PDF、Word 和 Excel 文件。");
        this.clearUploadFile();
        return;
      }
      if (this.uploadLoading) {
        this.$message.warning("已有资料正在处理，请等待完成后再上传。");
        this.clearUploadFile();
        return;
      }

      this.uploadLoading = true;
      this.uploadFilename = filename;
      this.uploadProgress = 5;
      this.uploadStatus = "running";
      this.uploadMessage = "正在提交资料上传任务...";
      Api.museumRag.uploadDocument(
        file,
        {
          museum: this.queryForm.museum || "湖南省博物馆",
          exhibition: this.queryForm.exhibition || "长沙马王堆汉墓陈列"
        },
        (res) => {
          const data = this.unwrap(res);
          if (!data.job_id) {
            this.finishUpload("failed", "上传任务创建失败，请检查 RAG 服务返回结果。");
            return;
          }
          this.uploadProgress = 10;
          this.uploadMessage = data.message || "资料已上传，正在后台解析和向量化...";
          this.pollUploadJob(data.job_id);
        },
        () => {
          this.finishUpload("failed", "资料上传失败，请检查 RAG 服务和文件格式。");
        }
      );
      this.clearUploadFile();
    },
    clearUploadFile: function () {
      if (this.$refs.documentUpload) {
        this.$refs.documentUpload.clearFiles();
      }
    },
    pollUploadJob: function (jobId) {
      this.stopUploadPolling();
      const poll = () => {
        Api.museumRag.getUploadJob(
          jobId,
          (res) => {
            const job = this.unwrap(res);
            const steps = Array.isArray(job.steps) ? job.steps : [];
            const completed = steps.filter((step) => step.status === "completed").length;
            this.uploadProgress = Math.max(this.uploadProgress, Math.min(99, Math.round(completed * 100 / Math.max(steps.length, 1))));
            this.uploadMessage = job.message || "正在处理资料...";
            if (job.status === "completed") {
              this.finishUpload("completed", job.message || "资料处理完成。");
              this.loadDocuments();
            } else if (job.status === "failed") {
              this.finishUpload("failed", job.error || job.message || "资料处理失败。");
            }
          },
          () => {
            this.finishUpload("failed", "无法获取资料处理进度，请刷新列表确认结果。");
          }
        );
      };
      poll();
      this.uploadPollTimer = setInterval(poll, 2000);
    },
    stopUploadPolling: function () {
      if (this.uploadPollTimer) {
        clearInterval(this.uploadPollTimer);
        this.uploadPollTimer = null;
      }
    },
    finishUpload: function (status, message) {
      this.stopUploadPolling();
      this.uploadStatus = status;
      this.uploadMessage = message;
      this.uploadProgress = status === "completed" ? 100 : this.uploadProgress;
      this.uploadLoading = false;
      if (status === "completed") {
        this.$message.success(message);
      } else if (status === "failed") {
        this.$message.error(message);
      }
    },
    deleteDocument: function (document) {
      this.$confirm(`确定删除资料“${document.filename}”吗？删除后需要重新上传才能恢复。`, "删除确认", {
        type: "warning"
      }).then(() => {
        this.deletingFilename = document.filename;
        Api.museumRag.deleteDocument(
          document.filename,
          (res) => {
            const data = this.unwrap(res);
            if (!data.job_id) {
              this.deletingFilename = "";
              this.$message.error("删除任务创建失败。");
              return;
            }
            this.pollDeleteJob(data.job_id, document.filename);
          },
          () => {
            this.deletingFilename = "";
            this.$message.error("删除资料失败，请检查 RAG 服务。");
          }
        );
      }).catch(() => {});
    },
    pollDeleteJob: function (jobId, filename) {
      this.stopDeletePolling();
      const poll = () => {
        Api.museumRag.getDeleteJob(
          jobId,
          (res) => {
            const job = this.unwrap(res);
            if (job.status === "completed") {
              this.deletingFilename = "";
              this.$message.success(`已删除资料“${filename}”。`);
              this.loadDocuments();
            } else if (job.status === "failed") {
              this.deletingFilename = "";
              this.$message.error(job.error || job.message || "删除资料失败。");
            }
          },
          () => {
            this.deletingFilename = "";
            this.$message.error("无法获取删除进度，请刷新列表确认结果。");
          }
        );
      };
      poll();
      this.deletePollTimer = setInterval(() => {
        if (!this.deletingFilename) {
          this.stopDeletePolling();
          return;
        }
        poll();
      }, 2000);
    },
    stopDeletePolling: function () {
      if (this.deletePollTimer) {
        clearInterval(this.deletePollTimer);
        this.deletePollTimer = null;
      }
    },
    openWorkbench: function () {
      if (!this.workbenchUrl) {
        this.workbenchMessage = "未配置知识库工作台地址，请先设置 VUE_APP_MUSEUM_WORKBENCH_URL。";
        return;
      }
      this.workbenchLoading = true;
      this.workbenchMessage = "正在申请知识库免登录票据...";
      Api.museumRag.getWorkbenchLoginUrl(
        (res) => {
          const data = this.unwrap(res);
          const targetUrl = data && typeof data.url === "string" ? data.url.trim() : "";
          if (!targetUrl) {
            this.workbenchMessage = "未获取到免登录地址，日常操作请继续在本页完成。";
            this.workbenchLoading = false;
            this.$message.warning(this.workbenchMessage);
            return;
          }
          this.workbenchMessage = "免登录票据已生成，正在打开知识库工作台。";
          this.workbenchLoading = false;
          window.open(targetUrl, "_blank");
        },
        () => {
          this.workbenchMessage = "知识库工作台免登录失败，日常操作请继续在本页完成。";
          this.workbenchLoading = false;
          this.$message.warning(this.workbenchMessage);
        }
      );
    },
    activateUpload: function () {
      this.activeWorkspace = "documents";
      this.$nextTick(() => {
        const upload = this.$refs.documentUpload;
        const input = upload && upload.$el ? upload.$el.querySelector('input[type="file"]') : null;
        if (input) {
          input.click();
        }
      });
    },
    runQuery: function () {
      const question = (this.queryForm.question || "").trim();
      if (!question) {
        this.$message.warning("请先输入游客问题。");
        return;
      }
      this.queryLoading = true;
      this.queryResult = null;
      Api.museumRag.query(
        {
          question,
          museum: this.queryForm.museum || "湖南省博物馆",
          exhibition: this.queryForm.exhibition || "长沙马王堆汉墓陈列",
          top_k: this.queryForm.top_k || 3,
          need_trace: true,
          scene: "manager_console"
        },
        (res) => {
          this.queryResult = this.unwrap(res);
          this.queryLoading = false;
        },
        (err) => {
          this.queryLoading = false;
          this.queryResult = {
            code: -1,
            message: "检索失败",
            contexts: [],
            trace: {},
            details: [err && err.message ? err.message : "请检查 manager-api、SuperMew 和桥接密钥配置。"]
          };
          this.$message.error("博物馆知识库检索失败，请检查服务是否启动。");
        }
      );
    },
    clearResult: function () {
      this.queryResult = null;
    },
    formatScore: function (item) {
      const score = item.rerank_score || item.score;
      if (score === undefined || score === null || score === "") {
        return "";
      }
      const numeric = Number(score);
      if (Number.isNaN(numeric)) {
        return String(score);
      }
      return numeric.toFixed(4);
    },
    formatDate: function (value) {
      if (!value) {
        return "—";
      }
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return String(value);
      }
      return new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      }).format(date);
    }
  }
};
</script>

<style scoped>
.museum-knowledge-page {
  min-height: 100vh;
  background: var(--museum-background);
}

.museum-main {
  padding: 96px 28px 36px;
}

.hero-card,
.query-card,
.result-card {
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 14px 40px rgba(31, 45, 90, 0.08);
}

.hero-card {
  max-width: 1180px;
  margin: 0 auto 24px;
  padding: 32px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 28px;
  background:
    radial-gradient(circle at 88% 12%, rgba(125, 211, 252, 0.35), transparent 30%),
    linear-gradient(135deg, var(--museum-text) 0%, var(--museum-primary) 62%, #7dd3fc 100%);
  color: #fff;
}

.eyebrow {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hero-copy h1 {
  margin: 16px 0 12px;
  font-size: 34px;
  line-height: 1.2;
}

.hero-copy p {
  margin: 0;
  max-width: 720px;
  line-height: 1.8;
  opacity: 0.92;
}

.hero-actions {
  margin-top: 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.workbench-message {
  margin-top: 14px !important;
  font-size: 13px;
}

.hero-status {
  align-self: stretch;
  padding: 22px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.14);
  backdrop-filter: blur(6px);
}

.status-title {
  margin-bottom: 18px;
  font-weight: 700;
}

.status-row {
  padding: 12px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.18);
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 12px;
  font-size: 13px;
}

.status-row span {
  opacity: 0.75;
}

.status-row strong {
  word-break: break-all;
}

.query-layout {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 420px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.documents-card {
  max-width: 1180px;
  margin: 0 auto 24px;
  padding: 24px;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 14px 40px rgba(31, 45, 90, 0.08);
}

.documents-heading {
  align-items: center;
}

.document-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.document-alert {
  margin-bottom: 16px;
}

.upload-progress {
  margin-bottom: 18px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #f7f9ff;
}

.upload-progress-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--museum-text);
  font-size: 13px;
  font-weight: 600;
}

.upload-progress p {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 12px;
}

.document-table {
  width: 100%;
}

.document-name {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--museum-text);
  font-weight: 600;
}

.document-name span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-profile {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #64748b;
  font-size: 12px;
  line-height: 1.4;
}

.delete-document-button {
  color: #ef4444;
}

.query-card,
.result-card {
  padding: 24px;
}

.section-heading {
  margin-bottom: 18px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.section-heading h2 {
  margin: 0 0 6px;
  color: var(--museum-text);
  font-size: 22px;
}

.section-heading p {
  margin: 0;
  color: #6b7280;
  line-height: 1.7;
}

.section-heading code {
  padding: 2px 6px;
  border-radius: 6px;
  background: var(--museum-primary-soft);
  color: var(--museum-primary-hover);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2px;
}

.query-actions {
  display: flex;
  gap: 10px;
}

.loading-box,
.empty-result {
  min-height: 180px;
  border: 1px dashed #d7def5;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #6b7280;
  background: #fbfcff;
}

.context-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.context-item {
  padding: 18px;
  border: 1px solid #e6ebf6;
  border-radius: 18px;
  background: #fbfcff;
}

.context-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
  color: #64748b;
  font-size: 12px;
}

.context-index {
  color: var(--museum-primary);
  font-weight: 700;
}

.context-item p {
  margin: 0;
  color: #1f2937;
  line-height: 1.8;
  white-space: pre-wrap;
}

.trace-box {
  margin-top: 16px;
  color: #4b5563;
}

.trace-box summary {
  cursor: pointer;
}

.trace-box pre {
  margin: 10px 0 0;
  padding: 14px;
  border-radius: 12px;
  overflow: auto;
  background: #111827;
  color: #d1d5db;
  font-size: 12px;
}

@media (max-width: 980px) {
  .hero-card,
  .query-layout {
    grid-template-columns: 1fr;
  }

  .documents-heading {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>

<style scoped>
.museum-knowledge-page {
  min-height: 100vh;
  background: var(--museum-background);
}

.museum-main {
  width: min(1440px, calc(100% - 48px));
  margin: 0 auto;
  padding: 92px 0 40px;
}

.hero-card {
  max-width: none;
  min-height: 250px;
  margin: 0 0 20px;
  padding: 36px 40px;
  grid-template-columns: minmax(0, 1fr) 430px;
  align-items: center;
  border: 1px solid var(--museum-border);
  border-radius: var(--museum-radius-lg);
  color: var(--museum-text);
  background: linear-gradient(110deg, #fffdf8 0%, #f8f5ef 58%, #efe1ca 100%);
  box-shadow: var(--museum-shadow-sm);
}

.hero-copy {
  position: relative;
  z-index: 1;
}

.eyebrow {
  border: 1px solid rgba(181, 138, 76, 0.34);
  color: var(--museum-primary-hover);
  background: rgba(255, 255, 255, 0.7);
  font-weight: 600;
}

.hero-copy h1 {
  color: var(--museum-text);
  font-size: 36px;
}

.hero-copy p {
  color: var(--museum-text-secondary);
  opacity: 1;
}

.hero-visual {
  height: 220px;
  overflow: hidden;
  border-radius: 18px;
}

.hero-visual img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.workbench-message {
  max-width: 640px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.summary-card {
  min-height: 112px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 7px;
  border: 1px solid var(--museum-border);
  border-radius: var(--museum-radius-md);
  background: var(--museum-surface);
  box-shadow: var(--museum-shadow-sm);
  text-align: left;
}

.summary-label,
.summary-card small {
  color: var(--museum-text-muted);
  font-size: 12px;
}

.summary-card > strong {
  color: var(--museum-text);
  font-size: 28px;
  line-height: 1.15;
}

.summary-card .summary-scope,
.summary-card .summary-status {
  font-size: 18px;
}

.summary-status {
  color: var(--museum-success) !important;
}

.summary-card-error .summary-status {
  color: var(--museum-danger) !important;
}

.workspace-card {
  padding: 8px 24px 28px;
  border: 1px solid var(--museum-border);
  border-radius: var(--museum-radius-lg);
  background: var(--museum-surface);
  box-shadow: var(--museum-shadow-sm);
}

.workspace-tabs::v-deep .el-tabs__header {
  margin-bottom: 28px;
}

.workspace-tabs::v-deep .el-tabs__item {
  height: 58px;
  padding: 0 24px;
  color: var(--museum-text-secondary);
  font-size: 16px;
  line-height: 58px;
}

.workspace-tabs::v-deep .el-tabs__item.is-active,
.workspace-tabs::v-deep .el-tabs__item:hover {
  color: var(--museum-primary-hover);
}

.workspace-tabs::v-deep .el-tabs__active-bar {
  height: 3px;
  background: var(--museum-primary);
}

.documents-heading {
  align-items: center;
}

.section-heading h2 {
  color: var(--museum-text);
}

.section-heading p {
  color: var(--museum-text-secondary);
}

.section-heading code {
  color: var(--museum-primary-hover);
  background: var(--museum-primary-soft);
}

.document-toolbar {
  display: grid;
  grid-template-columns: minmax(240px, 360px) 240px 1fr;
  gap: 12px;
  align-items: center;
  margin: 20px 0 16px;
  padding: 14px;
  border: 1px solid var(--museum-border);
  border-radius: var(--museum-radius-md);
  background: #fcfaf6;
}

.document-count {
  justify-self: end;
  color: var(--museum-text-muted);
  font-size: 13px;
}

.upload-progress {
  border: 1px solid var(--museum-border);
  background: #fcfaf6;
}

.upload-progress-title {
  color: var(--museum-text);
}

.document-name {
  color: var(--museum-text);
}

.document-name .file-icon {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: var(--museum-primary-hover);
  background: var(--museum-primary-soft);
}

.document-name > div,
.document-profile {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.document-name strong {
  overflow: hidden;
  color: var(--museum-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.document-name small,
.document-profile span {
  color: var(--museum-text-muted);
  font-size: 12px;
}

.document-profile strong {
  color: var(--museum-text-secondary);
  font-weight: 500;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 9px;
  border-radius: 999px;
  color: var(--museum-success);
  background: rgba(47, 133, 90, 0.1);
  font-size: 12px;
}

.retrieval-layout {
  display: grid;
  grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
  gap: 22px;
  align-items: start;
}

.query-card,
.result-card {
  padding: 24px;
  border: 1px solid var(--museum-border);
  border-radius: var(--museum-radius-md);
  box-shadow: none;
}

.query-card {
  background: #fcfaf6;
}

.result-card {
  min-height: 470px;
  background: var(--museum-surface);
}

.question-suggestions {
  margin: -4px 0 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  color: var(--museum-text-muted);
  font-size: 12px;
}

.question-suggestions button,
.advanced-toggle {
  padding: 0;
  border: 0;
  color: var(--museum-primary-hover);
  background: transparent;
  cursor: pointer;
}

.question-suggestions button:hover,
.advanced-toggle:hover {
  text-decoration: underline;
}

.advanced-toggle {
  min-height: 40px;
  margin-bottom: 8px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
}

.form-grid {
  padding: 14px;
  border: 1px solid var(--museum-border);
  border-radius: var(--museum-radius-sm);
  background: var(--museum-surface);
}

.form-grid::v-deep .el-form-item:last-child {
  margin-bottom: 4px;
}

.loading-box,
.empty-result {
  border-color: var(--museum-border);
  color: var(--museum-text-secondary);
  background: #fcfaf6;
}

.loading-box > i,
.empty-result > i {
  color: var(--museum-primary);
  font-size: 26px;
}

.loading-box > div,
.empty-result > div {
  display: flex;
  flex-direction: column;
  gap: 5px;
  text-align: left;
}

.loading-box strong,
.empty-result strong {
  color: var(--museum-text);
}

.loading-box span,
.empty-result span {
  color: var(--museum-text-muted);
  font-size: 13px;
}

.context-item {
  padding: 0;
  overflow: hidden;
  border-color: var(--museum-border);
  border-radius: var(--museum-radius-md);
  background: #fffdf9;
}

.context-header {
  padding: 14px 16px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  gap: 11px;
  align-items: center;
  border-bottom: 1px solid var(--museum-border);
  background: #fcfaf6;
}

.context-index {
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  color: #fff;
  background: var(--museum-primary);
}

.context-source {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
  text-align: left;
}

.context-source strong {
  overflow: hidden;
  color: var(--museum-text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-source span {
  color: var(--museum-text-muted);
  font-size: 12px;
}

.context-item > p {
  padding: 16px;
  color: var(--museum-text);
}

.context-meta {
  color: var(--museum-text-muted);
}

.trace-box {
  padding-top: 15px;
  border-top: 1px solid var(--museum-border);
  color: var(--museum-text-secondary);
}

.trace-box summary {
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--museum-text-secondary);
}

.trace-box > p {
  margin: 0 0 8px;
  color: var(--museum-text-muted);
  font-size: 12px;
}

@media (max-width: 1100px) {
  .hero-card,
  .retrieval-layout {
    grid-template-columns: 1fr;
  }

  .hero-visual {
    display: none;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 768px) {
  .museum-main {
    width: calc(100% - 24px);
  }

  .hero-card {
    padding: 26px 22px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .workspace-card {
    padding: 4px 14px 20px;
  }

  .documents-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .document-toolbar {
    grid-template-columns: 1fr;
  }

  .document-count {
    justify-self: start;
  }
}
</style>
