<template>
  <div class="museum-knowledge-page">
    <HeaderBar />
    <main class="museum-main">
      <section class="redirect-card">
        <div class="redirect-icon">
          <i class="el-icon-loading"></i>
        </div>
        <h1>正在进入博物馆知识库工作台</h1>
        <p class="redirect-desc">
          当前入口会直接跳转到 `SuperMew-main` 的现成页面，不再停留在小智后台做中间展示。
        </p>
        <div class="redirect-url">
          {{ workbenchUrl }}
        </div>
        <div class="redirect-actions">
          <el-button type="primary" icon="el-icon-right" @click="openWorkbench">
            立即进入
          </el-button>
          <el-button icon="el-icon-refresh" @click="redirectToWorkbench">
            重新跳转
          </el-button>
        </div>
        <p v-if="redirectMessage" class="redirect-message">
          {{ redirectMessage }}
        </p>
      </section>
    </main>
  </div>
</template>

<script>
import HeaderBar from "@/components/HeaderBar.vue";
import Api from "@/apis/api";

export default {
  name: "MuseumKnowledge",
  components: { HeaderBar },
  data: function () {
    return {
      workbenchUrl: (process.env.VUE_APP_MUSEUM_WORKBENCH_URL || "http://127.0.0.1:8000/").trim(),
      redirectMessage: "",
      redirectTimer: null
    };
  },
  mounted: function () {
    this.redirectToWorkbench();
  },
  beforeDestroy: function () {
    if (this.redirectTimer) {
      clearTimeout(this.redirectTimer);
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
      this.redirectToWorkbench(true);
    },
    redirectToWorkbench: function (manual) {
      if (typeof manual === "undefined") {
        manual = false;
      }
      if (!this.workbenchUrl) {
        this.redirectMessage = "未配置知识库工作台地址，请先设置 VUE_APP_MUSEUM_WORKBENCH_URL。";
        return;
      }
      this.redirectMessage = "正在申请知识库免登录票据...";
      Api.museumRag.getWorkbenchLoginUrl(
        (res) => {
          const data = this.unwrap(res);
          const targetUrl = (data.url || "").trim() || this.workbenchUrl;
          this.redirectMessage = "免登录票据已生成，正在进入知识库工作台...";
          if (this.redirectTimer) {
            clearTimeout(this.redirectTimer);
          }
          this.redirectTimer = setTimeout(() => {
            window.location.assign(targetUrl);
          }, manual ? 0 : 150);
        },
        () => {
          this.redirectMessage = "免登录失败，正在回退到普通工作台入口...";
          if (this.redirectTimer) {
            clearTimeout(this.redirectTimer);
          }
          this.redirectTimer = setTimeout(() => {
            window.location.assign(this.workbenchUrl);
          }, 300);
        }
      );
    },
  },
};
</script>

<style scoped>
.museum-knowledge-page {
  min-height: 100vh;
  background: #f5f7fb;
}

.museum-main {
  padding: 96px 28px 32px;
}

.redirect-card {
  max-width: 760px;
  margin: 48px auto 0;
  padding: 36px 32px;
  border-radius: 24px;
  background: linear-gradient(135deg, #263b73 0%, #5b7cfa 58%, #7dd3fc 100%);
  color: #fff;
  box-shadow: 0 16px 40px rgba(38, 59, 115, 0.22);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.redirect-icon {
  font-size: 34px;
  margin-bottom: 18px;
}

.redirect-card h1 {
  margin: 0;
  font-size: 32px;
  font-weight: 800;
}

.redirect-desc {
  margin: 14px 0 0;
  max-width: 620px;
  line-height: 1.8;
  opacity: 0.92;
}

.redirect-url {
  margin-top: 18px;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.14);
  word-break: break-all;
  font-size: 13px;
}

.redirect-actions {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}

.redirect-message {
  margin: 16px 0 0;
  font-size: 13px;
  opacity: 0.9;
}
</style>
