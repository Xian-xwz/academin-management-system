<template>
  <div class="h-[calc(100vh-64px)] flex flex-col w-full bg-white relative">
    <!-- 顶部导航 -->
    <div class="h-14 flex items-center justify-between px-4 sm:px-6 border-b border-gray-100 shrink-0">
      <div class="flex items-center">
        <el-dropdown trigger="click" @command="handleSessionChange">
          <span class="flex items-center cursor-pointer text-lg font-semibold text-gray-800 hover:bg-gray-100 px-3 py-1.5 rounded-lg transition-colors">
            {{ currentSessionTitle }}
            <el-icon class="ml-1 text-gray-500 text-sm"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu class="w-72">
              <el-dropdown-item command="">
                <div class="flex items-center text-blue-600 font-medium py-1">
                  <el-icon class="mr-2"><Plus /></el-icon>
                  开启新会话
                </div>
              </el-dropdown-item>
              <el-dropdown-item divided disabled>
                <div class="text-xs text-gray-400 font-semibold uppercase tracking-wider py-1">历史会话</div>
              </el-dropdown-item>
              <el-dropdown-item 
                v-for="s in aiChatStore.historySessions" 
                :key="s.id" 
                :command="s.id"
                class="hover:bg-gray-50"
              >
                <div class="flex items-center justify-between gap-2 py-1.5 w-full">
                  <div class="min-w-0 flex-1">
                    <div class="text-sm text-gray-800 truncate pr-2">{{ s.title }}</div>
                    <div class="text-[11px] text-gray-400 mt-0.5">{{ s.time }}</div>
                  </div>
                  <el-button
                    circle
                    link
                    size="small"
                    type="danger"
                    title="删除历史会话"
                    @click.stop="handleDeleteSession(s.id)"
                  >
                    <el-icon><Minus /></el-icon>
                  </el-button>
                </div>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <div class="flex items-center space-x-3">
        <span v-if="aiChatStore.conversationId" class="text-xs font-mono text-gray-400">
          ID: {{ aiChatStore.conversationId.split('-').pop() }}
        </span>
        <el-button plain round size="small" @click="handleNewSession">
          <el-icon class="mr-1"><Plus /></el-icon>新建会话
        </el-button>
      </div>
    </div>
    
    <!-- 聊天内容区 -->
    <div class="flex-1 relative h-0">
      <ChatWindow ref="chatWindowRef" :current-major="currentMajor" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import ChatWindow from '@/components/ChatWindow/index.vue';
import { Plus, ArrowDown, Minus } from '@element-plus/icons-vue';
import { useAiChatStore } from '@/stores/aiChat';
import { useUserStore } from '@/stores/user';
import { ElMessage, ElMessageBox } from 'element-plus';

const aiChatStore = useAiChatStore();
const userStore = useUserStore();
const chatWindowRef = ref<InstanceType<typeof ChatWindow> | null>(null);

const currentMajor = computed(() => userStore.userInfo?.majorName || '电子科学与技术');

const currentSessionTitle = computed(() => {
  if (!aiChatStore.conversationId) return '学业问询助手';
  const session = aiChatStore.historySessions.find(s => s.id === aiChatStore.conversationId);
  return session ? session.title : '学业问询助手';
});

onMounted(() => {
  aiChatStore.loadHistorySessions().catch(() => {
    ElMessage.warning('历史会话加载失败');
  });
});

const handleNewSession = () => {
  aiChatStore.clearSession();
  if (chatWindowRef.value) {
    chatWindowRef.value.clearMessages();
  }
};

const handleSessionChange = async (val: string) => {
  if (val === '') {
    handleNewSession();
  } else {
    aiChatStore.setConversationId(val);
    if (chatWindowRef.value) {
      try {
        await chatWindowRef.value.loadHistorySession(val);
        ElMessage.success('已加载历史对话');
      } catch (error: any) {
        ElMessage.error(error.message || '历史对话加载失败');
      }
    }
  }
};

const handleDeleteSession = async (id: string) => {
  try {
    await ElMessageBox.confirm('确定删除这条历史会话吗？删除后不可恢复。', '删除历史会话', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    });
    await aiChatStore.deleteHistorySession(id);
    if (chatWindowRef.value && !aiChatStore.conversationId) {
      chatWindowRef.value.clearMessages();
    }
    ElMessage.success('历史会话已删除');
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除历史会话失败');
    }
  }
};
</script>

<style scoped>
</style>
