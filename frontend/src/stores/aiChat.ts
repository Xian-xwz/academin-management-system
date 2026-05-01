import { defineStore } from 'pinia';
import { ref } from 'vue';
import { deleteChatConversation, getChatConversations } from '@/api/modules/ai';

export interface ChatSession {
  id: string;
  title?: string;
  time?: string;
}

export const useAiChatStore = defineStore('aiChat', () => {
  const conversationId = ref<string>('');
  const historySessions = ref<ChatSession[]>([]);

  const setConversationId = (id: string) => {
    conversationId.value = id;
  };

  const loadHistorySessions = async () => {
    historySessions.value = await getChatConversations();
  };

  const deleteHistorySession = async (id: string) => {
    await deleteChatConversation(id);
    historySessions.value = historySessions.value.filter(session => session.id !== id);
    if (conversationId.value === id) {
      conversationId.value = '';
    }
  };

  const clearSession = () => {
    conversationId.value = '';
  };

  return {
    conversationId,
    historySessions,
    setConversationId,
    loadHistorySessions,
    deleteHistorySession,
    clearSession,
  };
});
