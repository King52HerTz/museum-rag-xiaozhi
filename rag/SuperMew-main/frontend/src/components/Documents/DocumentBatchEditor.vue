<template>
  <div class="document-batch-panel">
    <div class="document-batch-header">
      <div>
        <h4><i class="fas fa-layer-group"></i> 批量编辑画像</h4>
        <p>先勾选文档，再勾选要改写的字段，未勾选字段会原样保留</p>
      </div>
      <div class="document-batch-actions">
        <button type="button" class="btn-secondary btn-compact" @click="emit('toggle-select-all')">
          <i class="fas fa-check-double"></i>
          {{ allFilteredSelected ? '取消全选当前结果' : '全选当前结果' }}
        </button>
        <button type="button" class="btn-secondary btn-compact" @click="emit('clear-selection')" :disabled="selectedCount === 0">
          <i class="fas fa-xmark"></i> 清空选择
        </button>
      </div>
    </div>

    <div class="document-batch-summary">
      已选择 {{ selectedCount }} 份文档，当前筛选结果中命中 {{ selectedFilteredCount }} 份
    </div>

    <div class="document-batch-grid">
      <label class="document-batch-field">
        <span class="document-batch-toggle">
          <input :checked="applyState.museum" type="checkbox" @change="onApplyChange('museum', $event)" />
          <span>批量改写博物馆</span>
        </span>
        <input
          :value="profile.museum"
          type="text"
          placeholder="例如：湖南省博物馆"
          :disabled="!applyState.museum"
          @input="onProfileInput('museum', $event)"
        />
      </label>
      <label class="document-batch-field">
        <span class="document-batch-toggle">
          <input :checked="applyState.exhibition" type="checkbox" @change="onApplyChange('exhibition', $event)" />
          <span>批量改写展览</span>
        </span>
        <input
          :value="profile.exhibition"
          type="text"
          placeholder="例如：长沙马王堆汉墓陈列"
          :disabled="!applyState.exhibition"
          @input="onProfileInput('exhibition', $event)"
        />
      </label>
      <label class="document-batch-field">
        <span class="document-batch-toggle">
          <input :checked="applyState.exhibit_id" type="checkbox" @change="onApplyChange('exhibit_id', $event)" />
          <span>批量改写展品编号</span>
        </span>
        <input
          :value="profile.exhibit_id"
          type="text"
          placeholder="例如：MWD-THBH-001"
          :disabled="!applyState.exhibit_id"
          @input="onProfileInput('exhibit_id', $event)"
        />
      </label>
      <label class="document-batch-field">
        <span class="document-batch-toggle">
          <input :checked="applyState.era" type="checkbox" @change="onApplyChange('era', $event)" />
          <span>批量改写时代</span>
        </span>
        <input
          :value="profile.era"
          type="text"
          placeholder="例如：西汉"
          :disabled="!applyState.era"
          @input="onProfileInput('era', $event)"
        />
      </label>
      <label class="document-batch-field">
        <span class="document-batch-toggle">
          <input :checked="applyState.category" type="checkbox" @change="onApplyChange('category', $event)" />
          <span>批量改写类别</span>
        </span>
        <input
          :value="profile.category"
          type="text"
          placeholder="例如：帛画、服饰、青铜器"
          :disabled="!applyState.category"
          @input="onProfileInput('category', $event)"
        />
      </label>
    </div>

    <div class="document-batch-footer">
      <button type="button" class="btn-secondary btn-compact" @click="emit('reset')">
        <i class="fas fa-rotate-left"></i> 重置批量面板
      </button>
      <button type="button" class="btn-primary" @click="emit('submit')" :disabled="saving || selectedCount === 0">
        <i :class="saving ? 'fas fa-spinner fa-spin' : 'fas fa-save'"></i>
        {{ saving ? '批量保存中...' : '批量保存画像' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DocumentBatchApplyState, DocumentProfilePayload } from '@/types/document';

const props = defineProps<{
  selectedCount: number;
  selectedFilteredCount: number;
  allFilteredSelected: boolean;
  applyState: DocumentBatchApplyState;
  profile: DocumentProfilePayload;
  saving: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:apply-state', value: DocumentBatchApplyState): void;
  (e: 'update:profile', value: DocumentProfilePayload): void;
  (e: 'toggle-select-all'): void;
  (e: 'clear-selection'): void;
  (e: 'reset'): void;
  (e: 'submit'): void;
}>();

const updateApplyState = (key: keyof DocumentBatchApplyState, checked: boolean) => {
  emit('update:apply-state', {
    ...props.applyState,
    [key]: checked,
  });
};

const updateProfile = (key: keyof DocumentProfilePayload, value: string) => {
  emit('update:profile', {
    ...props.profile,
    [key]: value.trim(),
  });
};

const onApplyChange = (key: keyof DocumentBatchApplyState, event: Event) => {
  updateApplyState(key, (event.target as HTMLInputElement).checked);
};

const onProfileInput = (key: keyof DocumentProfilePayload, event: Event) => {
  updateProfile(key, (event.target as HTMLInputElement).value);
};
</script>
