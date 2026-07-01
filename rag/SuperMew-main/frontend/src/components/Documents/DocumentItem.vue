<template>
  <div 
    class="document-item" 
    :class="{ deleting: documentStore.deleteJobs[doc.filename]?.status === 'running' }"
  >
    <div class="document-main">
      <div class="document-row">
        <div class="document-info">
          <label v-if="selectable" class="document-select">
            <input
              type="checkbox"
              :checked="selected"
              @change="emit('toggle-select', doc.filename)"
            />
            <span>选择</span>
          </label>
          <div class="document-icon">
            <i :class="getFileIcon(doc.file_type)"></i>
          </div>
          <div class="document-details">
            <div class="document-name">{{ doc.filename }}</div>
            <div class="document-meta">
              <span>{{ doc.file_type }}</span>
              <span>{{ doc.chunk_count }} 个文本片段</span>
            </div>
            <div v-if="metadataTags.length" class="document-tags">
              <span v-for="tag in metadataTags" :key="tag.label + tag.value" class="document-tag">
                {{ tag.label }}：{{ tag.value }}
              </span>
            </div>
          </div>
        </div>
        <div class="document-actions">
          <button @click="toggleProfileEditor" class="btn-secondary btn-compact" type="button">
            <i :class="isProfileOpen ? 'fas fa-chevron-up' : 'fas fa-pen-to-square'"></i>
            {{ isProfileOpen ? '收起画像' : '编辑画像' }}
          </button>
          <button
            @click="onDelete"
            class="btn-danger"
            title="删除文档"
            :disabled="documentStore.isDeleteActionLocked(doc.filename)"
          >
            <i :class="documentStore.getDeleteButtonIcon(doc.filename)"></i>
          </button>
        </div>
      </div>

      <div v-if="isProfileOpen" class="document-profile-card">
        <div class="document-profile-header">
          <h4><i class="fas fa-tags"></i> 结构化画像</h4>
          <span>更新后会直接影响结构化过滤命中范围</span>
        </div>
        <div class="document-profile-grid">
          <label class="document-profile-field">
            <span>博物馆</span>
            <input v-model.trim="profileForm.museum" type="text" placeholder="例如：湖南省博物馆" />
          </label>
          <label class="document-profile-field">
            <span>展览</span>
            <input v-model.trim="profileForm.exhibition" type="text" placeholder="例如：长沙马王堆汉墓陈列" />
          </label>
          <label class="document-profile-field">
            <span>展品编号</span>
            <input v-model.trim="profileForm.exhibit_id" type="text" placeholder="例如：MWD-THBH-001" />
          </label>
          <label class="document-profile-field">
            <span>时代</span>
            <input v-model.trim="profileForm.era" type="text" placeholder="例如：西汉" />
          </label>
          <label class="document-profile-field">
            <span>类别</span>
            <input v-model.trim="profileForm.category" type="text" placeholder="例如：帛画、服饰、青铜器" />
          </label>
        </div>
        <div class="document-profile-actions">
          <button type="button" class="btn-secondary btn-compact" @click="resetProfileForm">
            <i class="fas fa-rotate-left"></i> 还原当前值
          </button>
          <button
            type="button"
            class="btn-primary"
            @click="onSaveProfile"
            :disabled="documentStore.isProfileSaving(doc.filename)"
          >
            <i :class="documentStore.isProfileSaving(doc.filename) ? 'fas fa-spinner fa-spin' : 'fas fa-save'"></i>
            {{ documentStore.isProfileSaving(doc.filename) ? '保存中...' : '保存画像' }}
          </button>
        </div>
      </div>

      <!-- Deletion Progress Tracking -->
      <div
        v-if="documentStore.deleteJobs[doc.filename]"
        class="upload-progress delete-progress"
        :class="{ collapsed: documentStore.deleteJobs[doc.filename].collapsed }"
      >
        <button type="button" class="upload-progress-header" @click="onToggleCollapse">
          <span class="upload-message">{{ documentStore.deleteJobs[doc.filename].message || '删除进度' }}</span>
          <span class="upload-toggle">{{ documentStore.deleteJobs[doc.filename].collapsed ? '展开' : '收起' }}</span>
        </button>
        
        <div v-show="!documentStore.deleteJobs[doc.filename].collapsed" class="upload-step-list">
          <div
            v-for="step in documentStore.deleteJobs[doc.filename].steps"
            :key="step.key"
            class="upload-step"
            :class="`upload-step-${step.status}`"
          >
            <div class="upload-step-header">
              <span class="upload-step-label">{{ step.label }}</span>
              <span class="upload-step-percent">{{ step.percent }}%</span>
            </div>
            <div class="upload-step-bar">
              <div class="upload-step-fill" :style="{ width: step.percent + '%' }"></div>
            </div>
            <div v-if="step.message" class="upload-step-message">{{ step.message }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useDocumentStore } from '@/stores/documents';
import type { DocumentItem, DocumentProfilePayload } from '@/types/document';

const props = defineProps<{
  doc: DocumentItem;
  selectable?: boolean;
  selected?: boolean;
}>();

const emit = defineEmits<{
  (e: 'toggle-select', filename: string): void;
}>();

const documentStore = useDocumentStore();
const isProfileOpen = ref(false);
const profileForm = ref<DocumentProfilePayload>(documentStore.normalizeDocumentProfile(props.doc));
const selectable = computed(() => Boolean(props.selectable));
const selected = computed(() => Boolean(props.selected));

watch(
  () => props.doc,
  (nextDoc) => {
    profileForm.value = documentStore.normalizeDocumentProfile(nextDoc);
  },
  { deep: true }
);

const metadataTags = computed(() => {
  const tags = [
    { label: '馆', value: props.doc.museum || '' },
    { label: '展', value: props.doc.exhibition || '' },
    { label: '编号', value: props.doc.exhibit_id || '' },
    { label: '时代', value: props.doc.era || '' },
    { label: '类别', value: props.doc.category || '' },
  ];
  return tags.filter((item) => item.value);
});

const getFileIcon = (fileType: string) => {
  if (fileType === 'PDF') {
    return 'fas fa-file-pdf';
  } else if (fileType === 'Word') {
    return 'fas fa-file-word';
  } else if (fileType === 'Excel') {
    return 'fas fa-file-excel';
  }
  return 'fas fa-file';
};

const toggleProfileEditor = () => {
  isProfileOpen.value = !isProfileOpen.value;
};

const resetProfileForm = () => {
  profileForm.value = documentStore.normalizeDocumentProfile(props.doc);
};

const onSaveProfile = async () => {
  try {
    const updated = await documentStore.updateDocumentProfile(props.doc.filename, profileForm.value);
    profileForm.value = documentStore.normalizeDocumentProfile(updated);
  } catch (error: any) {
    alert(error.message);
  }
};

const onDelete = async () => {
  try {
    await documentStore.deleteDocument(props.doc.filename);
  } catch (error: any) {
    alert(error.message);
  }
};

const onToggleCollapse = () => {
  documentStore.toggleDeleteJobCollapsed(props.doc.filename);
};
</script>
