<template>
  <div class="museum-knowledge-page">
    <HeaderBar />
    <main class="museum-main">
      <section class="hero-card">
        <div class="hero-copy">
          <div class="eyebrow">Museum RAG</div>
          <h1>博物馆知识库</h1>
          <p>
            这里是智博导览管理平台对接 SuperMew RAG 的统一入口。资料上传和完整知识库管理仍在
            SuperMew 工作台完成；导览问答测试可直接在本页面调用桥接接口。
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
}
</style>
