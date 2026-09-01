<template>
  <Teleport to="body">
    <Transition name="museum-dialog">
      <div
        v-if="open"
        class="museum-dialog-backdrop"
        role="presentation"
        @mousedown.self="emit('cancel')"
      >
        <section
          class="museum-dialog-panel"
          role="alertdialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          :aria-describedby="messageId"
          tabindex="-1"
        >
          <div class="museum-dialog-icon" aria-hidden="true">
            <i class="fas fa-trash-can"></i>
          </div>
          <div class="museum-dialog-copy">
            <p class="museum-dialog-eyebrow">操作确认</p>
            <h3 :id="titleId">{{ title }}</h3>
            <p :id="messageId">{{ message }}</p>
          </div>
          <div class="museum-dialog-actions">
            <button type="button" class="museum-dialog-btn secondary" @click="emit('cancel')">
              {{ cancelText }}
            </button>
            <button
              ref="confirmButtonRef"
              type="button"
              class="museum-dialog-btn danger"
              :disabled="busy"
              @click="emit('confirm')"
            >
              <i v-if="busy" class="fas fa-spinner fa-spin" aria-hidden="true"></i>
              {{ busy ? '正在处理' : confirmText }}
            </button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue';

const props = withDefaults(defineProps<{
  open: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  busy?: boolean;
}>(), {
  confirmText: '确认',
  cancelText: '取消',
  busy: false,
});

const emit = defineEmits<{
  (event: 'confirm'): void;
  (event: 'cancel'): void;
}>();

const confirmButtonRef = ref<HTMLButtonElement | null>(null);
const titleId = 'museum-dialog-title-' + Math.random().toString(36).slice(2);
const messageId = 'museum-dialog-message-' + Math.random().toString(36).slice(2);

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Escape' && !props.busy) {
    emit('cancel');
  }
};

watch(() => props.open, async (open) => {
  if (open) {
    document.addEventListener('keydown', handleKeydown);
    await nextTick();
    confirmButtonRef.value?.focus();
  } else {
    document.removeEventListener('keydown', handleKeydown);
  }
});

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeydown);
});
</script>
