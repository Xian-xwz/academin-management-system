<template>
  <div 
    class="flex flex-col h-full bg-white relative"
    @dragover.prevent
    @drop.prevent="handleDrop"
  >
    <!-- 聊天记录区 -->
    <div class="flex-1 overflow-y-auto w-full pb-40" ref="chatScrollRef">
      <div v-if="messages.length === 0" class="flex flex-col items-center justify-center h-full opacity-60">
        <el-icon class="text-5xl text-gray-300 mb-4"><ChatDotSquare /></el-icon>
        <div class="text-gray-500 font-medium">今天需要解答什么学业问题呢？</div>
      </div>
      
      <div 
        v-for="(msg, index) in messages" 
        :key="msg.id || index" 
        class="w-full flex justify-center py-6 transition-colors"
        :class="{'bg-gray-50': msg.role === 'assistant'}"
      >
        <div class="flex space-x-4 items-start w-full max-w-3xl px-4 sm:px-6">
          
          <el-avatar :size="32" class="shrink-0 flex items-center justify-center rounded-sm" :class="msg.role === 'user' ? 'bg-gray-200 text-gray-700' : 'bg-[#10a37f] text-white'">
            <span v-if="msg.role === 'user'" class="text-xs font-semibold">User</span>
            <el-icon v-else class="text-lg"><Service /></el-icon>
          </el-avatar>

          <div class="flex flex-col space-y-1 w-full min-w-0">
            <div class="font-semibold text-gray-800 text-[15px]">
              {{ msg.role === 'user' ? '您' : '学业问询助手' }}
            </div>

            <div v-if="msg.role === 'assistant' && msg.statusSteps?.length" class="mb-2 rounded-xl border border-emerald-100 bg-emerald-50/60 p-3 text-xs text-emerald-800">
              <div class="mb-1 font-semibold">处理过程</div>
              <div class="space-y-1">
                <div v-for="(step, stepIndex) in msg.statusSteps" :key="`${msg.id}-status-${stepIndex}`" class="flex items-center">
                  <span class="mr-2 h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                  <span>{{ step }}</span>
                </div>
              </div>
            </div>

            <div v-if="msg.role === 'assistant'" class="ai-markdown text-gray-800 leading-relaxed text-[15px] pt-0.5" v-html="renderMarkdown(msg.content)"></div>
            <div v-else class="text-gray-800 leading-relaxed text-[15px] whitespace-pre-wrap pt-0.5">
              {{ msg.content }}
            </div>
            
            <div v-if="msg.intent && msg.role === 'assistant'" class="flex items-center mt-2">
              <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-200 text-gray-600">
                <el-icon class="mr-1"><Aim /></el-icon>
                {{ getIntentLabel(msg.intent) }}
              </span>
            </div>

            <!-- 知识来源展示 -->
            <div v-if="msg.sources && msg.sources.length > 0" class="mt-3 w-full max-w-xl">
              <el-collapse class="!border-none !bg-transparent custom-collapse">
                <el-collapse-item>
                  <template #title>
                    <div class="text-xs text-gray-500 flex items-center font-medium bg-white px-2 py-1 border border-gray-200 rounded text-center">
                      <el-icon class="mr-1"><Document /></el-icon>
                      引用来源 ({{ msg.sources.length }})
                    </div>
                  </template>
                  <div class="space-y-2 mt-2">
                    <div v-for="(source, sIdx) in msg.sources" :key="sIdx" class="bg-white border border-gray-200 rounded p-3 text-sm flex flex-col">
                      <div class="font-semibold text-gray-700 mb-1 flex items-center justify-between">
                        <span class="truncate pr-2">{{ source.documentName || source.title }}</span>
                        <span v-if="source.score" class="text-[10px] bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">{{ (source.score * 100).toFixed(0) }}% 相关</span>
                      </div>
                      <div class="text-gray-500 text-xs line-clamp-2 leading-relaxed">{{ source.content }}</div>
                    </div>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 输入区 -->
    <div class="absolute bottom-0 left-0 right-0 pt-6 pb-6 px-4 bg-gradient-to-t from-white via-white to-transparent">
      <div class="max-w-3xl mx-auto relative">
        <!-- 已传附件列表 -->
        <div v-if="attachedFiles.length > 0" class="mb-3 flex flex-wrap gap-2 px-1">
          <div v-for="(file, index) in attachedFiles" :key="index" class="flex items-center bg-blue-50 border border-blue-100 text-blue-600 px-3 py-1.5 rounded-xl text-[13px] shadow-sm">
            <el-icon class="mr-1.5"><Document /></el-icon>
            <span class="max-w-[150px] truncate mr-2 font-medium">{{ file.name }}</span>
            <span v-if="file.uploading" class="mr-2 text-[11px] text-blue-400">上传中...</span>
            <el-icon class="cursor-pointer hover:text-blue-800 transition-colors" @click="removeFile(index)"><Close /></el-icon>
          </div>
        </div>

        <div class="relative flex items-end shadow-[0_0_15px_rgba(0,0,0,0.1)] bg-white border border-gray-300 rounded-2xl overflow-hidden focus-within:border-gray-400 focus-within:ring-1 focus-within:ring-gray-400 transition-all">
          <el-input 
            v-model="inputMsg" 
            type="textarea" 
            :autosize="{ minRows: 1, maxRows: 8 }"
            placeholder="给 AI 助手发送消息..." 
            resize="none"
            class="custom-chat-input w-full"
            @keydown.enter.exact.prevent="handleSend" 
          />
          <div class="absolute bottom-2 right-2 flex items-center space-x-1.5">
            <!-- 隐藏的 file input -->
            <input type="file" ref="fileInputRef" class="hidden" @change="handleFileChange" multiple />
            
            <el-button 
              circle
              class="w-8 h-8 !border-none !bg-gray-100 hover:!bg-gray-200 transition-colors focus:outline-none flex items-center justify-center text-gray-500"
              @click="fileInputRef?.click()"
            >
              <template #icon>
                <el-icon class="text-[15px]"><Paperclip /></el-icon>
              </template>
            </el-button>

            <el-button 
              type="primary" 
              circle
              class="w-8 h-8 !border-none !bg-black hover:!bg-gray-800 transition-colors focus:outline-none flex items-center justify-center disabled:!bg-gray-300 disabled:!text-white disabled:cursor-not-allowed"
              :disabled="!inputMsg.trim().length"
              :loading="loading" 
              @click="handleSend"
            >
              <template #icon>
                <el-icon class="text-white font-bold"><Top /></el-icon>
              </template>
            </el-button>
          </div>
        </div>
        <div class="text-center text-[11px] text-gray-400 mt-3">
          内容由 AI 生成，可能存在事实错误，请注意甄别。
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import MarkdownIt from 'markdown-it';
import { getChatHistory, sendMessageStream, uploadAiFile } from '@/api/modules/ai';
import { Document, Service, ChatDotSquare, Aim, Top, Paperclip, Close } from '@element-plus/icons-vue';
import { useAiChatStore } from '@/stores/aiChat';
import { useUserStore } from '@/stores/user';
import { ChatMessage, DifyChatFile, SendChatRequest } from '@/types/ai';
import { ElMessage } from 'element-plus';

const props = defineProps({
  currentMajor: {
    type: String,
    default: '电子科学与技术'
  }
});

const messages = ref<ChatMessage[]>([]);
const inputMsg = ref('');
const loading = ref(false);
const currentStreamStatus = ref('');
const chatScrollRef = ref<HTMLElement | null>(null);

const fileInputRef = ref<HTMLInputElement | null>(null);
const attachedFiles = ref<{name: string, size: number, file: File, uploading?: boolean}[]>([]);

const handleFileChange = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    Array.from(target.files).forEach(file => {
      attachedFiles.value.push({ name: file.name, size: file.size, file });
    });
    target.value = ''; // 重置 input，允许重复选择同名文件
  }
};

const handleDrop = (e: DragEvent) => {
  const files = e.dataTransfer?.files;
  if (files && files.length > 0) {
    Array.from(files).forEach(file => {
      attachedFiles.value.push({ name: file.name, size: file.size, file });
    });
  }
};

const removeFile = (index: number) => {
  attachedFiles.value.splice(index, 1);
};

const aiChatStore = useAiChatStore();
const userStore = useUserStore();

const emit = defineEmits(['send']);

const formatTime = () => {
  const d = new Date();
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

const generateId = () => `msg-${Date.now()}`;

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true
});

const renderMarkdown = (content: string) => markdown.render(content || '');

const getIntentLabel = (intent: string) => {
  const map: Record<string, string> = {
    'graduation_requirements': '毕业要求查询',
    'graduation_audit': '毕业资格审核',
    'course_advice': '选课建议',
    'general_qa': '通用问答'
  };
  return map[intent] || '未知意图';
};

const initializeGreeting = () => {
  const isAdmin = userStore.userInfo?.role === 'admin';
  const greeting = isAdmin
    ? '你好！我是学业问询助手。当前你处于辅导员/教务视角，我可以协助你：\n\n1. 按学号查询学生毕业进度\n2. 查看学生学业详情、课表和时间规划\n3. 解释培养方案、毕业要求和课程体系\n\n查询具体学生时，请直接提供目标学号。'
    : '你好！我是你的专属 AI 学习助手。基于内置知识库和你的学业数据，我可以为你解答：\n\n1. 毕业学分要求\n2. 你的剩余差距与修读进度\n3. 选课建议、课表和时间规划\n\n请问有什么我可以帮你的？';
  messages.value.push({ 
    id: generateId(),
    role: 'assistant', 
    content: greeting,
    createdAt: formatTime()
  });
};

onMounted(() => {
  initializeGreeting();
});

const scrollToBottom = () => {
  nextTick(() => {
    if (chatScrollRef.value) {
      chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight;
    }
  });
};

const sendFromExternal = (text: string) => {
  inputMsg.value = text;
  handleSend();
};

const clearMessages = () => {
  messages.value = [];
  inputMsg.value = '';
  attachedFiles.value = [];
  currentStreamStatus.value = '';
  initializeGreeting();
};

const loadHistorySession = async (id: string) => {
  messages.value = [];
  inputMsg.value = '';
  attachedFiles.value = [];
  currentStreamStatus.value = '';
  const history = await getChatHistory(id);
  messages.value = history.messages.map((message, index) => ({
    id: `history-${id}-${index}`,
    role: message.role,
    content: message.content,
    intent: message.intent,
    sources: message.sources,
    createdAt: ''
  }));
  scrollToBottom();
};

defineExpose({
  sendFromExternal,
  clearMessages,
  loadHistorySession
});

const handleSend = async () => {
  if (!inputMsg.value.trim() || loading.value) return;
  
  let pendingMsg = inputMsg.value.trim();
  const filesToUpload = [...attachedFiles.value];
  
  if (attachedFiles.value.length > 0) {
    const fileNames = attachedFiles.value.map(f => f.name).join(', ');
    pendingMsg = `[📎 附件: ${fileNames}]\n${pendingMsg}`;
  }

  messages.value.push({ 
    id: generateId(),
    role: 'user', 
    content: pendingMsg.trim(), 
    createdAt: formatTime() 
  });
  inputMsg.value = '';
  attachedFiles.value = []; // Clear files after sending
  loading.value = true;
  currentStreamStatus.value = '正在发送问题...';
  const assistantMessage: ChatMessage = { 
    id: generateId(),
    role: 'assistant', 
    content: '', 
    createdAt: formatTime(),
    statusSteps: [],
    currentStatus: ''
  };
  messages.value.push(assistantMessage);
  const assistantIndex = messages.value.length - 1;
  const getAssistantMessage = () => messages.value[assistantIndex];
  const addStatusStep = (message: string) => {
    const target = getAssistantMessage();
    currentStreamStatus.value = message;
    target.currentStatus = message;
    if (!target.statusSteps) target.statusSteps = [];
    if (target.statusSteps[target.statusSteps.length - 1] !== message) {
      target.statusSteps.push(message);
    }
  };
  scrollToBottom();
  
  try {
    const studentId = userStore.userInfo?.studentId || 'mock_student_001';
    let difyFiles: DifyChatFile[] = [];
    if (filesToUpload.length > 0) {
      addStatusStep('正在上传附件到 Dify...');
      difyFiles = await Promise.all(filesToUpload.map(async (item) => {
        item.uploading = true;
        const uploaded = await uploadAiFile(item.file);
        item.uploading = false;
        return {
          type: uploaded.type,
          transfer_method: 'local_file' as const,
          upload_file_id: uploaded.id
        };
      }));
    }
    
    const requestPayload: SendChatRequest = {
      query: pendingMsg,
      conversation_id: aiChatStore.conversationId || undefined,
      student_id: studentId,
      major_name: props.currentMajor,
      files: difyFiles,
      inputs: {
        student_id: studentId,
        major_name: props.currentMajor
      }
    };

    let streamBuffer = '';
    let streamEnded = false;
    let typingTimer: ReturnType<typeof setInterval> | null = null;
    let resolveTypingDone: (() => void) | null = null;
    const typingDone = new Promise<void>((resolve) => {
      resolveTypingDone = resolve;
    });

    const finishTypingIfDone = () => {
      if (streamEnded && !streamBuffer && !typingTimer) {
        resolveTypingDone?.();
      }
    };

    const startTyping = () => {
      if (typingTimer) return;
      typingTimer = setInterval(() => {
        if (streamBuffer) {
          const chunk = streamBuffer.slice(0, 2);
          streamBuffer = streamBuffer.slice(2);
          getAssistantMessage().content += chunk;
          scrollToBottom();
          return;
        }
        if (typingTimer) {
          clearInterval(typingTimer);
          typingTimer = null;
        }
        finishTypingIfDone();
      }, 28);
    };

    await sendMessageStream(requestPayload, {
      onMessage: (chunk) => {
        streamBuffer += chunk;
        startTyping();
      },
      onReplace: (answer) => {
        streamBuffer = '';
        getAssistantMessage().content = answer;
        scrollToBottom();
      },
      onStatus: (message) => {
        if (!message) return;
        const target = getAssistantMessage();
        currentStreamStatus.value = message;
        target.currentStatus = message;
        if (!target.statusSteps) target.statusSteps = [];
        if (target.statusSteps[target.statusSteps.length - 1] !== message) {
          target.statusSteps.push(message);
        }
        scrollToBottom();
      },
      onEnd: (res) => {
        if (res.conversation_id && !aiChatStore.conversationId) {
          aiChatStore.setConversationId(res.conversation_id);
        }
        void aiChatStore.loadHistorySessions();
        const target = getAssistantMessage();
        target.sources = res.sources;
        target.intent = res.intent;
        streamEnded = true;
        if (!target.content.trim() && !streamBuffer.trim()) {
          target.content = '已收到回复，但内容为空。';
        }
        finishTypingIfDone();
      },
      onError: (message) => {
        streamBuffer = '';
        streamEnded = true;
        getAssistantMessage().content = message;
        currentStreamStatus.value = '响应异常';
        finishTypingIfDone();
      }
    });
    streamEnded = true;
    finishTypingIfDone();
    await typingDone;
  } catch (error: any) {
    ElMessage.error(error.message || '服务出现异常，请稍后重试');
    messages.value.push({
      id: generateId(),
      role: 'assistant',
      content: '抱歉，服务出现异常。',
      createdAt: formatTime()
    });
  } finally {
    loading.value = false;
    currentStreamStatus.value = '';
    scrollToBottom();
  }
};
</script>

<style scoped>
/* Remove Element Plus collapse default borders */
:deep(.custom-collapse .el-collapse-item__header) {
  border-bottom: none;
  background-color: transparent;
  height: auto;
  line-height: inherit;
}
:deep(.custom-collapse .el-collapse-item__wrap) {
  border-bottom: none;
  background-color: transparent;
}

/* Custom Input Styling */
:deep(.custom-chat-input .el-textarea__inner) {
  border-radius: 1rem;
  padding: 14px 84px 14px 16px; /* Right padding mapped for dual buttons */
  border-color: transparent;
  background-color: transparent;
  font-size: 15px;
  line-height: 1.5;
  box-shadow: none !important;
}
:deep(.custom-chat-input .el-textarea__inner:focus) {
  outline: none;
  box-shadow: none !important;
}

:deep(.ai-markdown > *:first-child) {
  margin-top: 0;
}

:deep(.ai-markdown > *:last-child) {
  margin-bottom: 0;
}

:deep(.ai-markdown p) {
  margin: 0.45rem 0;
}

:deep(.ai-markdown h1),
:deep(.ai-markdown h2),
:deep(.ai-markdown h3) {
  margin: 0.85rem 0 0.45rem;
  font-weight: 700;
  color: #111827;
}

:deep(.ai-markdown h1) {
  font-size: 1.15rem;
}

:deep(.ai-markdown h2) {
  font-size: 1.05rem;
}

:deep(.ai-markdown h3) {
  font-size: 0.98rem;
}

:deep(.ai-markdown ul),
:deep(.ai-markdown ol) {
  margin: 0.5rem 0;
  padding-left: 1.35rem;
}

:deep(.ai-markdown ul) {
  list-style: disc;
}

:deep(.ai-markdown ol) {
  list-style: decimal;
}

:deep(.ai-markdown li) {
  margin: 0.2rem 0;
}

:deep(.ai-markdown strong) {
  font-weight: 700;
  color: #111827;
}

:deep(.ai-markdown code) {
  border-radius: 0.35rem;
  background: #e5e7eb;
  padding: 0.1rem 0.35rem;
  font-size: 0.88em;
  color: #111827;
}

:deep(.ai-markdown pre) {
  margin: 0.75rem 0;
  overflow-x: auto;
  border-radius: 0.75rem;
  background: #111827;
  padding: 0.85rem;
  color: #f9fafb;
}

:deep(.ai-markdown pre code) {
  background: transparent;
  padding: 0;
  color: inherit;
}

:deep(.ai-markdown blockquote) {
  margin: 0.75rem 0;
  border-left: 3px solid #cbd5e1;
  background: #f8fafc;
  padding: 0.5rem 0.75rem;
  color: #475569;
}

:deep(.ai-markdown table) {
  margin: 0.75rem 0;
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9em;
}

:deep(.ai-markdown th),
:deep(.ai-markdown td) {
  border: 1px solid #e5e7eb;
  padding: 0.45rem 0.55rem;
  text-align: left;
  vertical-align: top;
}

:deep(.ai-markdown th) {
  background: #f3f4f6;
  font-weight: 700;
}

:deep(.ai-markdown a) {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 2px;
}
</style>
