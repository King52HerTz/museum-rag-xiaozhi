<template>
  <div class="answer-feedback" aria-label="回答评价">
    <span class="answer-feedback-label">这个回答有帮助吗？</span>
    <button
      type="button"
      :class="['feedback-icon-btn', { active: feedback?.rating === 'helpful' }]"
      :aria-pressed="feedback?.rating === 'helpful'"
      aria-label="有帮助"
      :disabled="submitting || disabled"
      @click="submitHelpful"
    >
      <i class="far fa-thumbs-up"></i>
    </button>
    <button
      type="button"
      :class="['feedback-icon-btn', { active: feedback?.rating === 'not_helpful' }]"
      :aria-pressed="feedback?.rating === 'not_helpful'"
      aria-label="需要改进"
      :disabled="submitting || disabled"
      @click="showReasons = !showReasons"
    >
      <i class="far fa-thumbs-down"></i>
    </button>
    <span v-if="savedMessage" class="feedback-saved" role="status">{{ savedMessage }}</span>

    <div v-if="showReasons" class="feedback-reason-panel">
      <span class="feedback-reason-title">主要问题是什么？</span>
      <div class="feedback-reason-options">
        <button
          v-for="option in reasonOptions"
          :key="option.value"
          type="button"
          :class="['feedback-reason-chip', { active: reasonCode === option.value }]"
          :aria-pressed="reasonCode === option.value"
          @click="reasonCode = option.value"
        >{{ option.label }}</button>
      </div>
      <textarea
        v-model="comment"
        maxlength="500"
        rows="2"
        placeholder="可选：补充说明具体哪里需要改进"
        aria-label="反馈补充说明"
      ></textarea>
      <div class="feedback-reason-actions">
        <button type="button" class="btn-secondary" @click="showReasons = false">取消</button>
        <button
          type="button"
          class="btn-primary"
          :disabled="!reasonCode || submitting"
          @click="submitNotHelpful"
        >{{ submitting ? '提交中…' : '提交反馈' }}</button>
      </div>
      <span v-if="errorMessage" class="feedback-error" role="alert">{{ errorMessage }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import api from '@/utils/api';
import type { AnswerFeedback } from '@/types/quality';

const props = defineProps<{
  sessionId: string;
  messageIndex: number;
  initialFeedback?: AnswerFeedback | null;
  disabled?: boolean;
}>();

const feedback = ref<AnswerFeedback | null>(props.initialFeedback || null);
const submitting = ref(false);
const showReasons = ref(false);
const reasonCode = ref(props.initialFeedback?.reason_code || '');
const comment = ref(props.initialFeedback?.comment || '');
const savedMessage = ref(props.initialFeedback ? '已记录' : '');
const errorMessage = ref('');

const reasonOptions = [
  { value: 'incorrect', label: '事实不准确' },
  { value: 'incomplete', label: '内容不完整' },
  { value: 'citation', label: '引用有问题' },
  { value: 'irrelevant', label: '答非所问' },
  { value: 'other', label: '其他' },
];

const submit = async (rating: 'helpful' | 'not_helpful') => {
  submitting.value = true;
  errorMessage.value = '';
  try {
    const response = await api.post('/quality/feedback', {
      session_id: props.sessionId,
      message_index: props.messageIndex,
      rating,
      reason_code: rating === 'not_helpful' ? reasonCode.value : null,
      comment: rating === 'not_helpful' ? comment.value.trim() : '',
    });
    feedback.value = response.data;
    savedMessage.value = rating === 'helpful' ? '感谢反馈' : '已加入改进队列';
    showReasons.value = false;
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || error.message || '反馈提交失败';
  } finally {
    submitting.value = false;
  }
};

const submitHelpful = () => submit('helpful');
const submitNotHelpful = () => submit('not_helpful');
</script>
