<template>
  <div v-if="sessionStore.showHistorySidebar" class="history-sidebar">
    <div class="history-header">
      <h3>历史会话</h3>
      <button @click="sessionStore.showHistorySidebar = false" class="close-btn">
        <i class="fas fa-times"></i>
      </button>
    </div>
    <div class="history-list">
      <div v-if="notice" class="history-notice" :class="notice.type" role="status">
        <i :class="notice.type === 'success' ? 'fas fa-circle-check' : 'fas fa-circle-exclamation'"></i>
        <span>{{ notice.message }}</span>
      </div>
      <div v-if="sessionStore.sessions.length === 0" class="empty-history">
        <p>暂无历史记录</p>
      </div>
      <div
        v-for="session in sessionStore.sessions"
        :key="session.session_id"
        class="history-item"
        :class="{ active: session.session_id === chatStore.sessionId }"
      >
        <div class="session-body" @click="onLoadSession(session.session_id)">
          <div class="session-info">
            <div class="session-title">{{ session.title || session.session_id }}</div>
            <div class="session-meta">
              <span>{{ session.message_count }} 条消息</span>
              <span>{{ new Date(session.updated_at).toLocaleString() }}</span>
            </div>
          </div>
        </div>
        <button
          class="history-delete-btn"
          title="删除会话"
          @click.stop="onDeleteSession(session.session_id)"
        >
          <i class="fas fa-trash"></i>
        </button>
      </div>
    </div>
    <MuseumConfirmDialog
      :open="Boolean(pendingDelete)"
      :title="'删除“' + (pendingDelete?.title || '') + '”？'"
      message="该会话及其聊天记录将被永久删除，此操作无法撤销。"
      confirm-text="删除会话"
      :busy="isDeleting"
      @cancel="cancelDelete"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useChatStore } from '@/stores/chat';
import { useSessionStore } from '@/stores/sessions';
import MuseumConfirmDialog from '@/components/MuseumConfirmDialog.vue';

const chatStore = useChatStore();
const sessionStore = useSessionStore();
const pendingDelete = ref<{ id: string; title: string } | null>(null);
const isDeleting = ref(false);
const notice = ref<{ type: 'success' | 'error'; message: string } | null>(null);
let noticeTimer: ReturnType<typeof setTimeout> | null = null;

const showNotice = (type: 'success' | 'error', message: string) => {
  notice.value = { type, message };
  if (noticeTimer) clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => {
    notice.value = null;
  }, 3200);
};

const onLoadSession = async (sessionId: string) => {
  try {
    await chatStore.loadSession(sessionId);
  } catch (error: any) {
    alert('加载会话失败：' + error.message);
  }
};

const onDeleteSession = (sessionId: string) => {
  const sessionLabel = sessionStore.sessions.find(s => s.session_id === sessionId)?.title || sessionId;
  pendingDelete.value = { id: sessionId, title: sessionLabel };
};

const cancelDelete = () => {
  if (!isDeleting.value) pendingDelete.value = null;
};

const confirmDelete = async () => {
  if (!pendingDelete.value || isDeleting.value) return;
  const sessionId = pendingDelete.value.id;
  isDeleting.value = true;
  try {
    const successMsg = await sessionStore.deleteSession(sessionId);
    if (chatStore.sessionId === sessionId) {
      chatStore.messages = [];
      chatStore.sessionId = 'session_' + Date.now();
      chatStore.activeNav = 'newChat';
    }
    pendingDelete.value = null;
    showNotice('success', successMsg);
  } catch (error: any) {
    showNotice('error', '删除会话失败：' + error.message);
  } finally {
    isDeleting.value = false;
  }
};
</script>
