<template>
  <div class="document-filters">
    <div class="document-filters-header">
      <div>
        <h4><i class="fas fa-filter"></i> 筛选与搜索</h4>
        <p>按馆藏画像快速筛出目标文档</p>
      </div>
      <button type="button" class="btn-secondary btn-compact" @click="emit('reset')">
        <i class="fas fa-rotate-left"></i> 重置筛选
      </button>
    </div>

    <div class="document-filters-grid">
      <label class="document-filter-field document-filter-field-wide">
        <span>关键词</span>
        <input
          :value="filters.keyword"
          type="text"
          placeholder="搜索文件名、编号、馆、展、时代、类别"
          @input="onKeywordInput"
        />
      </label>
      <label class="document-filter-field">
        <span>博物馆</span>
        <select :value="filters.museum" @change="onSelectChange('museum', $event)">
          <option value="">全部博物馆</option>
          <option v-for="item in museumOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label class="document-filter-field">
        <span>展览</span>
        <select :value="filters.exhibition" @change="onSelectChange('exhibition', $event)">
          <option value="">全部展览</option>
          <option v-for="item in exhibitionOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label class="document-filter-field">
        <span>时代</span>
        <select :value="filters.era" @change="onSelectChange('era', $event)">
          <option value="">全部时代</option>
          <option v-for="item in eraOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <label class="document-filter-field">
        <span>类别</span>
        <select :value="filters.category" @change="onSelectChange('category', $event)">
          <option value="">全部类别</option>
          <option v-for="item in categoryOptions" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
    </div>

    <div class="document-filter-summary">
      当前显示 {{ filteredCount }} / {{ totalCount }} 份文档
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DocumentFilters } from '@/types/document';

const props = defineProps<{
  filters: DocumentFilters;
  museumOptions: string[];
  exhibitionOptions: string[];
  eraOptions: string[];
  categoryOptions: string[];
  filteredCount: number;
  totalCount: number;
}>();

const emit = defineEmits<{
  (e: 'update:filters', value: DocumentFilters): void;
  (e: 'reset'): void;
}>();

const updateFilter = (key: keyof DocumentFilters, value: string) => {
  emit('update:filters', {
    ...props.filters,
    [key]: value.trim(),
  });
};

const onKeywordInput = (event: Event) => {
  updateFilter('keyword', (event.target as HTMLInputElement).value);
};

const onSelectChange = (key: Exclude<keyof DocumentFilters, 'keyword'>, event: Event) => {
  updateFilter(key, (event.target as HTMLSelectElement).value);
};
</script>
