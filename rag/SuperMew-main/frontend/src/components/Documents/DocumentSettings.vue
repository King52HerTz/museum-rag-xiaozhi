<template>
  <div class="settings-panel">
    <div class="settings-header">
      <h2><i class="fas fa-cog"></i> 文档管理</h2>
      <p>上传文档进行向量化处理，支持 PDF 和 Word、Excel 格式</p>
    </div>

    <UploadSection />

    <div class="documents-section">
      <div class="documents-toolbar">
        <h3><i class="fas fa-list"></i> 已上传文档</h3>
        <button @click="onRefresh" class="btn-secondary" :disabled="documentStore.documentsLoading">
          <i class="fas fa-sync" :class="{ 'fa-spin': documentStore.documentsLoading }"></i> 刷新列表
        </button>
      </div>

      <div v-if="documentStore.documentsLoading" class="loading-indicator">
        加载中...
      </div>

      <div v-else-if="documentStore.documents.length === 0" class="empty-documents">
        <i class="fas fa-inbox"></i>
        <p>暂无文档</p>
      </div>

      <div v-else>
        <DocumentFilters
          :filters="filters"
          :museum-options="museumOptions"
          :exhibition-options="exhibitionOptions"
          :era-options="eraOptions"
          :category-options="categoryOptions"
          :filtered-count="filteredDocuments.length"
          :total-count="documentStore.documents.length"
          @update:filters="updateFilters"
          @reset="resetFilters"
        />

        <DocumentBatchEditor
          :selected-count="selectedCount"
          :selected-filtered-count="selectedFilteredCount"
          :all-filtered-selected="allFilteredSelected"
          :apply-state="batchApply"
          :profile="batchProfile"
          :saving="documentStore.batchProfileSaving"
          @update:apply-state="updateBatchApply"
          @update:profile="updateBatchProfile"
          @toggle-select-all="toggleSelectAllFiltered"
          @clear-selection="clearSelection"
          @reset="resetBatchEditor"
          @submit="submitBatchUpdate"
        />

        <div v-if="filteredDocuments.length === 0" class="empty-documents empty-filtered-documents">
          <i class="fas fa-search"></i>
          <p>当前筛选条件下没有匹配文档</p>
        </div>

        <div v-else class="documents-list">
          <DocumentItem
            v-for="doc in filteredDocuments"
            :key="doc.filename"
            :doc="doc"
            selectable
            :selected="selectedFilenames.includes(doc.filename)"
            @toggle-select="toggleSelection"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import UploadSection from './UploadSection.vue';
import DocumentItem from './DocumentItem.vue';
import DocumentFilters from './DocumentFilters.vue';
import DocumentBatchEditor from './DocumentBatchEditor.vue';
import { useDocumentManagement } from '@/composables/useDocumentManagement';

const {
  documentStore,
  filters,
  museumOptions,
  exhibitionOptions,
  eraOptions,
  categoryOptions,
  filteredDocuments,
  selectedFilenames,
  selectedCount,
  selectedFilteredCount,
  allFilteredSelected,
  batchApply,
  batchProfile,
  onRefresh,
  updateFilters,
  resetFilters,
  toggleSelection,
  toggleSelectAllFiltered,
  clearSelection,
  updateBatchApply,
  updateBatchProfile,
  resetBatchEditor,
  submitBatchUpdate,
  initialize,
  cleanup,
} = useDocumentManagement();

onMounted(() => {
  initialize();
});

onUnmounted(() => {
  cleanup();
});
</script>
