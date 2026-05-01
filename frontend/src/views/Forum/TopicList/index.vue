<template>
  <div class="max-w-3xl mx-auto pb-10">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-800">专业学习资料论坛</h2>
      <el-button type="primary" @click="$router.push('/forum/topics/create')" round>
        <el-icon class="mr-1"><Edit /></el-icon> 发布新话题
      </el-button>
    </div>

    <!-- 筛选和搜索栏 -->
    <div class="mb-6 bg-white p-4 rounded-2xl shadow-sm flex flex-col sm:flex-row gap-4 items-center">
      <el-input v-model="searchQuery" placeholder="搜索帖子标题、内容或标签" class="w-full sm:w-64" clearable>
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      
      <el-select v-model="filterMajor" placeholder="全部专业" class="w-full sm:w-40" clearable>
        <el-option label="全部专业" value="" />
        <el-option v-for="major in majors" :key="major.code" :label="major.name" :value="major.name" />
      </el-select>

      <div class="flex flex-1 justify-end w-full">
        <el-button type="primary" @click="handleSearch">查 询</el-button>
      </div>
    </div>

    <!-- 骨架屏 -->
    <el-skeleton :loading="loading" animated :count="3">
      <template #template>
        <div class="bg-white p-6 rounded-2xl shadow-sm mb-4">
          <div class="flex items-center space-x-4 mb-4">
            <el-skeleton-item variant="circle" style="width: 44px; height: 44px" />
            <div class="flex-1">
              <el-skeleton-item variant="text" style="width: 20%" />
              <el-skeleton-item variant="text" style="width: 30%; margin-top: 4px;" />
            </div>
          </div>
          <el-skeleton-item variant="p" style="width: 100%" />
          <el-skeleton-item variant="p" style="width: 80%; margin-top: 8px;" />
        </div>
      </template>
      <template #default>
        
        <!-- 朋友圈风格 feed 列表 -->
        <div class="space-y-4">
          <div v-for="topic in topics" :key="topic.id" class="bg-white p-5 sm:p-6 rounded-2xl shadow-sm cursor-pointer hover:shadow-md transition-shadow" @click="toggleExpanded(topic.id)">
            <!-- 头部：头像与信息 -->
            <div class="flex items-start space-x-3 sm:space-x-4">
              <el-avatar :size="44" :src="topic.authorAvatar" shape="square" class="!rounded-lg bg-gradient-to-br from-blue-400 to-indigo-500 text-white font-bold text-lg shrink-0 shadow-sm">
                {{ topic.author.charAt(0) }}
              </el-avatar>
              
              <div class="flex-1 min-w-0">
                <div class="flex justify-between items-start">
                  <div>
                    <h3 class="text-[15px] sm:text-base font-semibold text-blue-700 hover:text-blue-800 transition-colors">{{ topic.author }}</h3>
                    <div class="text-xs text-gray-400 mt-0.5">{{ topic.major }} · {{ topic.createTime }}</div>
                  </div>
                  <div class="flex items-center gap-1 shrink-0" @click.stop>
                    <el-button size="small" link type="primary" @click="$router.push(`/forum/topics/${topic.id}`)">详情</el-button>
                    <template v-if="topic.canEdit">
                      <el-button size="small" link type="primary" @click="$router.push(`/forum/topics/${topic.id}/edit`)">编辑</el-button>
                      <el-button size="small" link type="danger" @click="handleDeleteTopic(topic)">删除</el-button>
                    </template>
                  </div>
                </div>

                <!-- 正文内容 -->
                <div class="mt-3">
                  <h4 class="font-bold text-gray-900 mb-1 text-[15px]">{{ topic.title }}</h4>
                  <p class="text-gray-800 text-[14px] leading-relaxed whitespace-pre-wrap break-words" :class="{ 'line-clamp-3': !isExpanded(topic.id) }">
                    {{ topic.content }}
                  </p>
                  
                  <div class="mt-2" v-if="!isExpanded(topic.id) && topic.content.length > 80">
                    <span class="text-blue-500 text-sm hover:underline cursor-pointer" @click.stop="toggleExpanded(topic.id)">全文</span>
                  </div>
                </div>

                <!-- 标签 -->
                <div class="mt-3 flex flex-wrap gap-2">
                  <span v-for="tag in topic.tags" :key="tag" class="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100">
                    # {{ tag }}
                  </span>
                </div>

                <!-- 附件展示 -->
                <div v-if="topic.attachments && topic.attachments.length > 0 && isExpanded(topic.id)" class="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2" @click.stop>
                  <div v-for="(file, idx) in topic.attachments" :key="idx" class="flex items-center p-2 rounded-lg bg-gray-50 border border-gray-100 hover:bg-gray-100 transition-colors cursor-pointer" @click.stop="downloadFile(file)">
                    <div class="w-8 h-8 rounded bg-white flex items-center justify-center mr-2 text-blue-500 shrink-0 border border-gray-200">
                      <el-icon><Document /></el-icon>
                    </div>
                    <div class="min-w-0 flex-1">
                      <div class="text-xs font-medium text-gray-700 truncate" :title="file.name">{{ file.name }}</div>
                      <div class="text-[10px] text-gray-400 mt-0.5">{{ file.size }}</div>
                    </div>
                  </div>
                </div>

                <!-- 底部操作栏与数据 -->
                <div class="mt-4 flex justify-between items-center bg-gray-50/50 p-2 rounded-lg" @click.stop>
                  <div class="flex items-center space-x-4 sm:space-x-6 text-gray-500 text-[13px]">
                    <span title="浏览" class="flex items-center"><el-icon class="mr-1.5 min-w-[14px]"><View /></el-icon>{{ topic.views || 0 }}</span>
                  </div>
                  <div class="flex items-center space-x-3 sm:space-x-5 text-gray-500 text-[13px]">
                    <span class="flex items-center cursor-pointer hover:text-blue-500 transition-colors" @click="handleLike(topic)"><el-icon class="mr-1"><Star /></el-icon>赞 {{ topic.likes || 0 }}</span>
                    <span class="flex items-center cursor-pointer hover:text-blue-500 transition-colors" @click="toggleExpanded(topic.id)"><el-icon class="mr-1"><ChatDotSquare /></el-icon>评论 {{ topic.comments?.length || 0 }}</span>
                  </div>
                </div>

                <!-- 评论区 (类似朋友圈展开) -->
                <div v-if="isExpanded(topic.id)" class="mt-3 bg-[#f3f4f6] rounded-lg p-3 relative" @click.stop>
                  <!-- 向上小三角 -->
                  <div class="absolute -top-1.5 left-6 w-3 h-3 bg-[#f3f4f6] transform rotate-45 rounded-sm"></div>
                  
                  <div v-if="topic.comments && topic.comments.length > 0" class="space-y-1.5 text-[13px] relative z-10">
                    <div v-for="comment in topic.comments" :key="comment.id" class="leading-relaxed">
                      <span class="inline-flex items-center font-bold text-blue-700 cursor-pointer hover:underline">
                        <el-avatar :size="18" :src="comment.authorAvatar" class="mr-1 text-[10px] bg-blue-100 text-blue-600">{{ comment.author.charAt(0) }}</el-avatar>
                        {{ comment.author }}
                      </span>
                      <span class="text-gray-800 ml-1">：{{ comment.content }}</span>
                      <div v-if="comment.attachments && comment.attachments.length > 0" class="mt-1 ml-2 space-y-1">
                        <div
                          v-for="file in comment.attachments"
                          :key="file.id"
                          class="inline-flex max-w-full items-center rounded-md bg-blue-50 px-2 py-1 text-xs text-blue-700 cursor-pointer hover:bg-blue-100"
                          @click.stop="downloadFile(file)"
                        >
                          <el-icon class="mr-1 shrink-0"><Document /></el-icon>
                          <span class="truncate">{{ file.name }}</span>
                          <span class="ml-1 shrink-0 text-blue-400">({{ file.size }})</span>
                        </div>
                      </div>
                      <div class="mt-1 ml-2">
                        <input
                          :ref="(el) => setCommentFileInput(comment.id, el)"
                          type="file"
                          class="hidden"
                          @change="handleCommentFileChange(topic.id, comment, $event)"
                        />
                        <el-button size="small" link type="primary" :loading="uploadingCommentId === comment.id" @click.stop="openCommentFilePicker(comment.id)">
                          <el-icon class="mr-1"><Paperclip /></el-icon>上传评论附件
                        </el-button>
                      </div>
                      
                      <!-- 二级回复 -->
                      <div v-if="comment.replies && comment.replies.length > 0">
                        <div v-for="reply in comment.replies" :key="reply.id" class="mt-0.5 ml-2">
                          <span class="inline-flex items-center font-bold text-blue-700 cursor-pointer hover:underline">
                            <el-avatar :size="18" :src="reply.authorAvatar" class="mr-1 text-[10px] bg-blue-100 text-blue-600">{{ reply.author.charAt(0) }}</el-avatar>
                            {{ reply.author }}
                          </span>
                          <span class="text-gray-500 mx-1">回复</span>
                          <span class="font-bold text-blue-700 cursor-pointer hover:underline">{{ comment.author }}</span>
                          <span class="text-gray-800 ml-1">：{{ reply.content }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-center text-gray-400 text-xs py-2 relative z-10">
                    暂无评论，来抢沙发吧~
                  </div>

                  <!-- 快速回复框 -->
                  <div class="mt-3 flex items-center space-x-2 relative z-10">
                    <el-input v-model="replyContent[topic.id]" size="small" placeholder="评论..." class="flex-1" @keyup.enter="submitComment(topic.id)" />
                    <el-button type="primary" size="small" :loading="replyLoading[topic.id]" @click="submitComment(topic.id)">发送</el-button>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>
      </template>
    </el-skeleton>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue';
import { getTopics, getForumMajors, addComment, likeTopic, downloadForumFile, uploadCommentFile, deleteTopic } from '@/api/modules/forum';
import { Search, View, ChatDotSquare, Star, Edit, Document, Paperclip } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useUserStore } from '@/stores/user';

const userStore = useUserStore();
const topics = ref<any[]>([]);
const majors = ref<Array<{ code: string; name: string }>>([]);
const loading = ref(false);

const searchQuery = ref('');
const filterMajor = ref('');

const expandedIds = ref<number[]>([]);
const replyContent = reactive<Record<number, string>>({});
const replyLoading = reactive<Record<number, boolean>>({});
const uploadingCommentId = ref<number | null>(null);
const commentFileInputs = ref<Record<number, HTMLInputElement>>({});

const fetchTopics = async () => {
  loading.value = true;
  try {
    topics.value = await getTopics({
      q: searchQuery.value,
      major: filterMajor.value,
      sort: 'latest' // Default to latest for feed
    }) as any;
  } finally {
    loading.value = false;
  }
}

const handleSearch = () => {
  fetchTopics();
};

const fetchMajors = async () => {
  try {
    majors.value = await getForumMajors();
  } catch (error: any) {
    ElMessage.warning(error.message || '专业筛选项加载失败');
  }
};

const toggleExpanded = (id: number) => {
  const index = expandedIds.value.indexOf(id);
  if (index === -1) {
    expandedIds.value.push(id);
  } else {
    expandedIds.value.splice(index, 1);
  }
};

const isExpanded = (id: number) => {
  return expandedIds.value.includes(id);
};

const handleLike = async (topic: any) => {
  const res: any = await likeTopic(topic.id);
  topic.likes = res.likes;
  topic.liked = res.liked;
  ElMessage.success('已点赞');
};

const handleDeleteTopic = async (topic: any) => {
  try {
    await ElMessageBox.confirm(`确定删除话题「${topic.title}」吗？`, '删除话题', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    });
    await deleteTopic(topic.id);
    topics.value = topics.value.filter(item => item.id !== topic.id);
    ElMessage.success('话题已删除');
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除话题失败');
    }
  }
};

const downloadFile = async (file: any) => {
  try {
    await downloadForumFile(file);
  } catch (error: any) {
    ElMessage.error(error.message || '附件下载失败');
  }
};

const setCommentFileInput = (commentId: number, el: Element | null) => {
  if (el instanceof HTMLInputElement) {
    commentFileInputs.value[commentId] = el;
  }
};

const openCommentFilePicker = (commentId: number) => {
  commentFileInputs.value[commentId]?.click();
};

const handleCommentFileChange = async (topicId: number, comment: any, event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;

  uploadingCommentId.value = comment.id;
  try {
    const uploaded = await uploadCommentFile(topicId, comment.id, file);
    if (!comment.attachments) comment.attachments = [];
    comment.attachments.push(uploaded);
    ElMessage.success('评论附件上传成功');
  } catch (error: any) {
    ElMessage.error(error.message || '评论附件上传失败');
  } finally {
    uploadingCommentId.value = null;
  }
};

const submitComment = async (topicId: number) => {
  const content = replyContent[topicId];
  if (!content || !content.trim()) {
    ElMessage.warning('请输入评论内容');
    return;
  }

  replyLoading[topicId] = true;
  try {
    const comment: any = await addComment(topicId, { content: content.trim() });
    
    // Update local data
    const topic = topics.value.find(t => t.id === topicId);
    if (topic) {
      if (!topic.comments) topic.comments = [];
      topic.comments.push(comment || {
        id: Date.now(),
        author: userStore.userInfo?.name || '当前测试用户',
        content: content.trim(),
        createTime: '刚刚',
        replies: []
      });
      replyContent[topicId] = '';
      ElMessage.success('评论成功');
    }
  } finally {
    replyLoading[topicId] = false;
  }
};

onMounted(() => {
  fetchMajors();
  fetchTopics();
});
</script>

<style scoped>
/* Hidden default scrollbars for cleaner look */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
