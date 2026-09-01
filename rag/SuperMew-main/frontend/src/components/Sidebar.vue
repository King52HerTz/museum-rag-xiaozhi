<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo-icon"><img :src="zhiboMark" alt="" /></div>
      <div class="brand-copy">
        <h2>智博导览</h2>
        <small>知识库工作台</small>
      </div>
    </div>
    <nav class="sidebar-nav">
      <button @click="onNewChat" :class="['nav-btn', { active: chatStore.activeNav === 'newChat' }]">
        <i class="fas fa-plus"></i> 新建会话
      </button>
      <button @click="onHistory" :class="['nav-btn', { active: chatStore.activeNav === 'history' }]">
        <i class="fas fa-history"></i> 历史记录
      </button>
      <button v-if="authStore.isAdmin" @click="onSettings" :class="['nav-btn', { active: chatStore.activeNav === 'settings' }]">
        <i class="fas fa-cog"></i> 设置
      </button>
    </nav>
    <div class="sidebar-footer">
      <button @click="showClearDialog = true" class="danger-btn">
        <i class="fas fa-trash-alt"></i> 清空当前对话
      </button>
      <div v-if="authStore.isAuthenticated" class="user-badge">
        <span>{{ authStore.currentUser?.username }}</span>
        <small>{{ authStore.currentUser?.role }}</small>
      </div>
      <button v-if="authStore.isAuthenticated" @click="authStore.handleLogout" class="danger-btn logout-btn">
        <i class="fas fa-right-from-bracket"></i> 退出登录
      </button>
    </div>
    <MuseumConfirmDialog
      :open="showClearDialog"
      title="清空当前对话？"
      message="当前页面中的对话内容将被清空，历史会话仍保留在记录中。"
      confirm-text="清空对话"
      @cancel="showClearDialog = false"
      @confirm="onClearChat"
    />
  </aside>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useChatStore } from '@/stores/chat';
import { useSessionStore } from '@/stores/sessions';
import MuseumConfirmDialog from '@/components/MuseumConfirmDialog.vue';
import zhiboMark from '@/assets/zhibo-mark.png';

const authStore = useAuthStore();
const chatStore = useChatStore();
const sessionStore = useSessionStore();
const showClearDialog = ref(false);

const onNewChat = () => {
  chatStore.handleNewChat();
};

const onClearChat = () => {
  chatStore.handleClearChat();
  showClearDialog.value = false;
};

const onHistory = async () => {
  chatStore.activeNav = 'history';
  sessionStore.showHistorySidebar = !sessionStore.showHistorySidebar;
  if (sessionStore.showHistorySidebar) {
    try {
      await sessionStore.fetchSessions();
    } catch (error: any) {
      alert(error.message);
    }
  }
};

const onSettings = () => {
  if (!authStore.isAdmin) {
    alert('仅管理员可访问文档管理');
    return;
  }
  chatStore.activeNav = 'settings';
  sessionStore.showHistorySidebar = false;
};
</script>
