<template>
  <div :class="['message', msg.isUser ? 'user-message' : 'bot-message']">
    <!-- User or finished AI answer -->
    <template v-if="msg.isUser">
      <MessageContent 
        :text="msg.text" 
        :is-user="true" 
        :msg-index="msgIndex" 
      />
    </template>
    
    <template v-else>
      <!-- RAG Thinking/Trace view -->
      <ThinkingTrace 
        v-if="msg.isThinking && !msg.text" 
        :msg="msg" 
        :msg-index="msgIndex" 
      />
      
      <!-- Actual response text -->
      <template v-else>
        <MessageContent 
          :text="msg.text" 
          :is-user="false" 
          :msg-index="msgIndex" 
          @cite-click="onCiteClick"
        />
        
        <!-- RAG Source documents -->
        <References 
          ref="referencesRef"
          :msg="msg" 
          :msg-index="msgIndex" 
          @cite-click="onCiteClick"
        />
        
        <!-- Deep retrieval traces logs -->
        <RetrievalTraceDetails :msg="msg" />

        <AnswerFeedback
          v-if="msg.ragTrace && !msg.isThinking"
          :session-id="chatStore.sessionId"
          :message-index="msgIndex"
          :initial-feedback="msg.feedback"
          :disabled="chatStore.isLoading"
        />
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import MessageContent from './MessageContent.vue';
import ThinkingTrace from './ThinkingTrace.vue';
import References from './References.vue';
import RetrievalTraceDetails from './RetrievalTraceDetails.vue';
import AnswerFeedback from './AnswerFeedback.vue';
import type { Message } from '@/types/chat';
import { useChatStore } from '@/stores/chat';

const props = defineProps<{
  msg: Message;
  msgIndex: number;
}>();

const chatStore = useChatStore();

const emit = defineEmits<{
  (e: 'cite-click', msgIndex: number, chunkIndex: number): void;
}>();

const referencesRef = ref<InstanceType<typeof References> | null>(null);

const openReferences = () => {
  referencesRef.value?.openDetails();
};

defineExpose({
  openReferences
});

const onCiteClick = (msgIndex: number, chunkIndex: number) => {
  emit('cite-click', msgIndex, chunkIndex);
};
</script>
