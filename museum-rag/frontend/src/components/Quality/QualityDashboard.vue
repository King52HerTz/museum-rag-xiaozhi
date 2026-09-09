<template>
  <div class="quality-panel">
    <div class="quality-header">
      <div>
        <span class="quality-eyebrow">RAG QUALITY CONTROL</span>
        <h2><i class="fas fa-chart-line"></i> 质量监控</h2>
        <p>从真实对话追踪检索质量，并把低质量回答转化为可处理的问题队列。</p>
      </div>
      <div class="quality-toolbar">
        <label>
          <span>统计周期</span>
          <select v-model.number="periodDays" @change="loadSummary">
            <option :value="7">近 7 天</option>
            <option :value="30">近 30 天</option>
            <option :value="90">近 90 天</option>
          </select>
        </label>
        <button class="btn-secondary" type="button" :disabled="loading" @click="loadSummary">
          <i class="fas fa-sync" :class="{ 'fa-spin': loading }"></i> 刷新
        </button>
      </div>
    </div>

    <div v-if="loading && !summary" class="quality-state">正在汇总质量数据…</div>
    <div v-else-if="errorMessage" class="quality-state quality-state-error" role="alert">
      {{ errorMessage }}
    </div>

    <template v-if="summary">
      <section class="quality-metrics" aria-label="质量核心指标">
        <article class="quality-metric-card metric-bronze">
          <span>RAG 回答</span>
          <strong>{{ summary.metrics.rag_answers }}</strong>
          <small>统计周期内有检索追踪的回答</small>
        </article>
        <article class="quality-metric-card metric-blue">
          <span>证据可回答率</span>
          <strong>{{ formatRate(summary.metrics.answerable_rate) }}</strong>
          <small>{{ summary.metrics.answerable_count }} 条证据充分</small>
        </article>
        <article class="quality-metric-card metric-green">
          <span>用户满意率</span>
          <strong>{{ formatNullableRate(summary.metrics.helpful_rate) }}</strong>
          <small>{{ summary.metrics.feedback_count }} 条有效评价</small>
        </article>
        <article class="quality-metric-card metric-coral">
          <span>待改进问题</span>
          <strong>{{ summary.failure_queue.length }}</strong>
          <small>差评、证据不足或检索降级</small>
        </article>
      </section>

      <section class="quality-grid">
        <article class="quality-card">
          <div class="quality-card-heading">
            <div>
              <h3>检索状态分布</h3>
              <p>快速识别知识缺口和检索异常</p>
            </div>
          </div>
          <div v-if="statusRows.length" class="status-bars">
            <div v-for="row in statusRows" :key="row.status" class="status-bar-row">
              <div class="status-bar-label">
                <span>{{ statusLabel(row.status) }}</span>
                <strong>{{ row.count }}</strong>
              </div>
              <div class="status-bar-track" aria-hidden="true">
                <span :class="`status-${row.status}`" :style="{ width: `${row.percent}%` }"></span>
              </div>
            </div>
          </div>
          <div v-else class="quality-empty">当前周期暂无 RAG 对话</div>
        </article>

        <article class="quality-card quality-health-card">
          <div class="quality-card-heading">
            <div>
              <h3>链路健康</h3>
              <p>精排、降级与官网补充运行情况</p>
            </div>
          </div>
          <dl class="quality-health-list">
            <div><dt>证据不足</dt><dd>{{ summary.metrics.partial_count }}</dd></div>
            <div><dt>知识库无资料</dt><dd>{{ summary.metrics.no_knowledge_count }}</dd></div>
            <div><dt>检索降级</dt><dd>{{ summary.metrics.degraded_count }}</dd></div>
            <div><dt>官网补充成功</dt><dd>{{ summary.metrics.web_success_count }} / {{ summary.metrics.web_attempt_count }}</dd></div>
            <div v-if="summary.metrics.web_extract_attempt_count"><dt>定向提取成功</dt><dd>{{ summary.metrics.web_extract_success_count }} / {{ summary.metrics.web_extract_attempt_count }}</dd></div>
          </dl>
        </article>
      </section>

      <section class="quality-card quality-queue-card">
        <div class="quality-card-heading">
          <div>
            <h3>失败问题队列</h3>
            <p>优先处理用户差评、证据不足和服务降级问题</p>
          </div>
          <span class="quality-count-badge">{{ summary.failure_queue.length }} 条</span>
        </div>
        <div v-if="summary.failure_queue.length" class="quality-run-list">
          <article v-for="run in summary.failure_queue" :key="runKey(run)" class="quality-run-item">
            <div class="quality-run-topline">
              <span :class="['quality-status', `status-${run.retrieval_status}`]">{{ statusLabel(run.retrieval_status) }}</span>
              <span v-if="run.rating === 'not_helpful'" class="quality-feedback-badge"><i class="far fa-thumbs-down"></i> 用户差评</span>
              <time>{{ formatTime(run.timestamp) }}</time>
            </div>
            <h4>{{ run.query || '未记录原问题' }}</h4>
            <p>{{ run.answer_excerpt }}</p>
            <div class="quality-run-meta">
              <span>用户：{{ run.username }}</span>
              <span>证据片段：{{ run.retrieved_count }}</span>
              <span v-if="run.reason_code">原因：{{ reasonLabel(run.reason_code) }}</span>
              <span v-if="run.degraded_code">错误码：{{ run.degraded_code }}</span>
              <span v-if="run.official_web_extract_error_code">提取错误：{{ run.official_web_extract_error_code }}</span>
            </div>
            <blockquote v-if="run.comment">“{{ run.comment }}”</blockquote>
          </article>
        </div>
        <div v-else class="quality-empty">当前周期没有待处理问题</div>
      </section>

      <section class="quality-card">
        <div class="quality-card-heading">
          <div>
            <h3>最近检索记录</h3>
            <p>保留查询、证据状态与重排链路，便于逐条复盘</p>
          </div>
        </div>
        <div v-if="summary.recent_runs.length" class="quality-table-wrap">
          <table class="quality-table">
            <thead><tr><th>时间</th><th>问题</th><th>状态</th><th>证据</th><th>精排</th><th>评价</th></tr></thead>
            <tbody>
              <tr v-for="run in summary.recent_runs" :key="runKey(run)">
                <td>{{ formatTime(run.timestamp) }}</td>
                <td class="quality-query-cell">{{ run.query || '—' }}</td>
                <td><span :class="['quality-status', `status-${run.retrieval_status}`]">{{ statusLabel(run.retrieval_status) }}</span></td>
                <td>{{ run.retrieved_count }}</td>
                <td>{{ run.rerank_applied ? (run.rerank_backend || '已执行') : '未执行' }}</td>
                <td>{{ ratingLabel(run.rating) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="quality-empty">暂无检索记录</div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import api from '@/utils/api';
import type { FeedbackRating, QualityRun, QualitySummary } from '@/types/quality';

const periodDays = ref(30);
const loading = ref(false);
const errorMessage = ref('');
const summary = ref<QualitySummary | null>(null);

const loadSummary = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    const response = await api.get('/quality/summary', {
      params: { days: periodDays.value, limit: 50 },
    });
    summary.value = response.data;
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || error.message || '质量数据加载失败';
  } finally {
    loading.value = false;
  }
};

const statusRows = computed(() => {
  const distribution = summary.value?.status_distribution || {};
  const total = summary.value?.metrics.rag_answers || 0;
  return Object.entries(distribution)
    .map(([status, count]) => ({
      status,
      count,
      percent: total ? Math.max((count / total) * 100, 3) : 0,
    }))
    .sort((a, b) => b.count - a.count);
});

const statusLabel = (status: string) => ({
  answerable: '证据充分',
  partial: '证据不足',
  no_knowledge: '无相关资料',
  insufficient_evidence: '检索降级',
  provider_failed: '服务异常',
  needs_clarification: '等待澄清',
  needs_scope_selection: '等待选择范围',
  unknown: '未知',
}[status] || status);

const reasonLabel = (reason: string) => ({
  incorrect: '事实不准确',
  incomplete: '内容不完整',
  citation: '引用有问题',
  irrelevant: '答非所问',
  other: '其他',
}[reason] || reason);

const ratingLabel = (rating?: FeedbackRating | null) => {
  if (rating === 'helpful') return '有帮助';
  if (rating === 'not_helpful') return '需改进';
  return '未评价';
};

const formatRate = (value: number) => `${Math.round(value * 100)}%`;
const formatNullableRate = (value: number | null) => value === null ? '—' : formatRate(value);
const formatTime = (value: string) => value ? new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—';
const runKey = (run: QualityRun) => `${run.session_id}-${run.message_index}`;

onMounted(loadSummary);
</script>
