<template>
  <div class="auth-panel">
    <div class="auth-brand">
      <span class="auth-brand-mark"><img :src="zhiboMark" alt="" /></span>
      <span><strong>智博导览</strong><small>SMART MUSEUM GUIDE</small></span>
    </div>
    <h2>{{ authStore.authMode === 'login' ? '登录智博导览知识库工作台' : '注册智博导览知识库工作台' }}</h2>
    <p>登录后即可使用文档上传、检索问答和历史会话；管理员可管理馆藏知识库。</p>
    <div class="auth-form">
      <input v-model="authStore.authForm.username" type="text" placeholder="用户名" @keyup.enter="onSubmit" />
      <input v-model="authStore.authForm.password" type="password" placeholder="密码" @keyup.enter="onSubmit" />
      
      <select v-if="authStore.authMode === 'register'" v-model="authStore.authForm.role">
        <option value="user">普通用户</option>
        <option value="admin">管理员</option>
      </select>
      
      <input 
        v-if="authStore.authMode === 'register' && authStore.authForm.role === 'admin'" 
        v-model="authStore.authForm.admin_code" 
        type="password" 
        placeholder="管理员邀请码" 
        @keyup.enter="onSubmit"
      />
      
      <button class="send-btn auth-submit" :disabled="authStore.authLoading" @click="onSubmit">
        {{ authStore.authLoading ? '提交中...' : (authStore.authMode === 'login' ? '登录' : '注册') }}
      </button>
      
      <button class="auth-switch" @click="toggleAuthMode">
        {{ authStore.authMode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth';
import zhiboMark from '@/assets/zhibo-mark.png';

const authStore = useAuthStore();

const toggleAuthMode = () => {
  authStore.authMode = authStore.authMode === 'login' ? 'register' : 'login';
};

const onSubmit = async () => {
  try {
    await authStore.handleAuthSubmit();
  } catch (error: any) {
    alert(error.message);
  }
};
</script>
