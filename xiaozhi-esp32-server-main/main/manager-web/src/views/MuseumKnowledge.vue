<template>
  <div class="museum-knowledge-page">
    <HeaderBar />
    <main class="museum-main">
      <section class="hero-card">
        <div class="hero-copy">
          <div class="eyebrow">Museum RAG</div>
          <h1>博物馆知识库</h1>
          <p>
            在智博导览管理平台内完成资料上传、处理状态查看和检索测试。SuperMew 工作台保留为高级维护入口，
            小智服务端会使用同一套博物馆知识库。
          </p>
          <div class="hero-actions">
            <el-button type="primary" icon="el-icon-right" :loading="workbenchLoading" @click="openWorkbench">
              进入知识库工作台
            </el-button>
            <el-button icon="el-icon-refresh" @click="fillDemoQuestion">
              使用演示问题
            </el-button>
          </div>
          <p v-if="workbenchMessage" class="workbench-message">
            {{ workbenchMessage }}
          </p>
        </div>
        <div class="hero-status">
          <div class="status-title">当前演示配置</div>
          <div class="status-row">
            <span>博物馆</span>
            <strong>{{ queryForm.museum }}</strong>
          </div>
          <div class="status-row">
            <span>展览</span>
            <strong>{{ queryForm.exhibition }}</strong>
          </div>
          <div class="status-row">
            <span>工作台</span>
            <strong>{{ workbenchUrl }}</strong>
          </div>
        </div>
      </section>

      <section class="documents-card">
        <div class="section-heading documents-heading">
          <div>
            <h2>知识库资料</h2>
            <p>支持 PDF、Word 和 Excel；上传后会在后台解析、分块并建立向量索引。</p>
          </div>
          <div class="document-actions">
            <el-button icon="el-icon-refresh" :loading="documentsLoading" @click="loadDocuments">
              刷新列表
            </el-button>
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
              <el-button type="primary" icon="el-icon-upload2" :loading="uploadLoading">
                上传资料
              </el-button>
            </el-upload>
          </div>
        </div>

        <el-alert
          v-if="uploadMessage"
          class="document-alert"
          :title="uploadMessage"
          :type="uploadStatus === 'failed' ? 'error' : 'info'"
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

        <el-table
          v-loading="documentsLoading"
          :data="documents"
          stripe
          class="document-table"
          empty-text="暂无资料，请先上传博物馆资料"
        >
          <el-table-column prop="filename" label="文件名" min-width="280">
            <template slot-scope="scope">
              <div class="document-name">
                <i class="el-icon-document"></i>
                <span>{{ scope.row.filename }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="file_type" label="格式" width="90" />
          <el-table-column prop="chunk_count" label="检索分块" width="110" />
          <el-table-column label="知识库画像" min-width="220">
            <template slot-scope="scope">
              <div class="document-profile">
                <span>{{ scope.row.museum || queryForm.museum }}</span>
                <span>{{ scope.row.exhibition || queryForm.exhibition }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right">
            <template slot-scope="scope">
              <el-button
                type="text"
                class="delete-document-button"
                :loading="deletingFilename === scope.row.filename"
                @click="deleteDocument(scope.row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="query-layout">
        <div class="query-card">
          <div class="section-heading">
            <div>
              <h2>导览问答测试</h2>
              <p>通过 manager-api 调用 SuperMew 的 <code>/api/museum/query</code> 检索型接口。</p>
            </div>
          </div>

          <el-form :model="queryForm" label-position="top" class="query-form">
            <el-form-item label="游客问题">
              <el-input
                v-model="queryForm.question"
                type="textarea"
                :rows="4"
                maxlength="300"
                show-word-limit
                placeholder="例如：马王堆汉墓的素纱单衣为什么这么有名？"
                @keyup.ctrl.enter.native="runQuery"
              />
            </el-form-item>
            <div class="form-grid">
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
                检索测试
              </el-button>
              <el-button icon="el-icon-delete" @click="clearResult">
                清空结果
              </el-button>
            </div>
          </el-form>
        </div>

        <div class="result-card">
          <div class="section-heading">
            <div>
              <h2>检索结果</h2>
              <p>这些片段会作为小智导览助手生成讲解话术的依据。</p>
            </div>
            <el-tag v-if="queryResult" :type="resultOk ? 'success' : 'warning'">
              {{ queryResult.message || '已返回' }}
            </el-tag>
          </div>

          <el-empty v-if="!queryResult && !queryLoading" description="还没有检索结果，先问一个湖南省博物馆问题吧。" />

          <div v-if="queryLoading" class="loading-box">
            <i class="el-icon-loading"></i>
            <span>正在检索博物馆知识库...</span>
          </div>

          <div v-if="queryResult && contexts.length === 0 && !queryLoading" class="empty-result">
            未检索到相关资料。可以先进入知识库工作台确认资料是否已上传并完成解析。
          </div>

          <div v-if="contexts.length > 0" class="context-list">
            <article v-for="item in contexts" :key="item.index || item.chunk_id || item.content" class="context-item">
              <div class="context-meta">
                <span class="context-index">#{{ item.index }}</span>
                <span>{{ item.title || item.source || '未知来源' }}</span>
                <span v-if="item.page_number">页码：{{ item.page_number }}</span>
                <span v-if="formatScore(item)">相关度：{{ formatScore(item) }}</span>
              </div>
              <p>{{ item.content }}</p>
            </article>
          </div>

          <details v-if="queryResult && queryResult.trace" class="trace-box">
            <summary>查看检索 trace</summary>
            <pre>{{ prettyTrace }}</pre>
          </details>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import Api from "@/apis/api";

const DEMO_QUESTIONS = [
  "马王堆汉墓的素纱单衣为什么这么有名？",
  "辛追夫人的发现对研究汉代生活有什么价值？",
  "湖南省博物馆里马王堆汉墓陈列适合怎么给游客讲解？"
];

export default {
  name: "MuseumKnowledge",
  components: { HeaderBar },
  data: function () {
    return {
      workbenchUrl: (process.env.VUE_APP_MUSEUM_WORKBENCH_URL || "http://127.0.0.1:8000/").trim(),
      workbenchMessage: "",
      workbenchLoading: false,
      documents: [],
      documentsLoading: false,
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
      queryForm: {
        question: DEMO_QUESTIONS[0],
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
    resultOk: function () {
      return this.queryResult && Number(this.queryResult.code) === 0;
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
          this.documentsLoading = false;
        },
        () => {
          this.documents = [];
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
          const targetUrl = (data.url || "").trim() || this.workbenchUrl;
          this.workbenchMessage = "免登录票据已生成，正在打开知识库工作台。";
          this.workbenchLoading = false;
          window.open(targetUrl, "_blank");
        },
        () => {
          this.workbenchMessage = "免登录失败，已回退到普通工作台入口。";
          this.workbenchLoading = false;
          window.open(this.workbenchUrl, "_blank");
        }
      );
    },
    fillDemoQuestion: function () {
      const currentIndex = DEMO_QUESTIONS.indexOf(this.queryForm.question);
      const nextIndex = currentIndex < 0 ? 0 : (currentIndex + 1) % DEMO_QUESTIONS.length;
      this.queryForm.question = DEMO_QUESTIONS[nextIndex];
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
    }
  }
};
</script>

<style scoped>
.museum-knowledge-page {
  min-height: 100vh;
  background: #f5f7fb;
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
    linear-gradient(135deg, #1f2f63 0%, #4f67df 62%, #7dd3fc 100%);
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
  color: #1f2f63;
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
  color: #1f2f63;
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
  color: #1f2f63;
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
  background: #eef2ff;
  color: #4f46e5;
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
  color: #4f67df;
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
