<template>
  <div class="max-w-4xl mx-auto space-y-6" v-loading="loading">
    <div class="bg-white rounded p-6 shadow-sm">
      <el-button @click="$router.push('/forum')" class="mb-4" plain>
        <el-icon class="mr-1"><ArrowLeft /></el-icon> 返回论坛
      </el-button>
      
      <div v-if="detail">
        <div v-if="detail.canEdit" class="mb-4 flex justify-end gap-2">
          <el-button size="small" type="primary" plain @click="$router.push(`/forum/topics/${detail.id}/edit`)">编辑话题</el-button>
          <el-button size="small" type="danger" plain @click="handleDeleteTopic">删除话题</el-button>
        </div>
        <h1 class="text-2xl md:text-3xl font-bold text-gray-900 mb-4">{{ detail.title }}</h1>
        <div class="flex items-center space-x-4 text-sm text-gray-500 border-b pb-4 mb-6">
          <el-avatar :size="36" :src="detail.authorAvatar" class="bg-blue-100 text-blue-600 font-bold">{{ detail.author.charAt(0) }}</el-avatar>
          <span class="font-medium text-gray-700">{{ detail.author }}</span>
          <span><el-icon><Reading /></el-icon> {{ detail.major }}</span>
          <span><el-icon><Clock /></el-icon> {{ detail.createTime }}</span>
        </div>
        
        <div class="mb-6 flex space-x-2">
          <el-tag v-for="tag in detail.tags" :key="tag" type="info">{{ tag }}</el-tag>
        </div>

        <div class="bg-gray-50 p-6 rounded mb-8 text-gray-800 leading-relaxed text-base min-h-[150px] whitespace-pre-wrap">
          {{ detail.content }}
        </div>

        <!-- 附件列表 -->
        <div v-if="detail.attachments && detail.attachments.length > 0" class="mb-8">
          <h3 class="font-bold text-gray-800 mb-3 flex items-center">
            <el-icon class="mr-2 text-blue-500"><Paperclip /></el-icon> 附件资料 ({{ detail.attachments.length }})
          </h3>
          <ul class="space-y-2">
            <li v-for="(file, idx) in detail.attachments" :key="idx" class="flex justify-between items-center p-3 border rounded bg-white hover:bg-gray-50">
              <div class="flex items-center">
                <el-icon class="text-blue-500 mr-2 text-lg"><Document /></el-icon>
                <span class="font-medium text-gray-700">{{ file.name }}</span>
                <span class="text-gray-400 text-sm ml-3">({{ file.size }})</span>
              </div>
              <el-button size="small" type="primary" plain @click="downloadFile(file)">下载</el-button>
            </li>
          </ul>
        </div>

        <!-- 评论区 -->
        <div>
          <h3 class="font-bold text-xl text-gray-800 mb-4 border-b pb-2">讨论与回复 ({{ detail.comments.length }})</h3>
          
          <div class="mb-6 bg-gray-50 p-4 rounded">
            <el-input
              v-model="newComment"
              type="textarea"
              :rows="3"
              placeholder="分享你的见解或提出疑问..."
              class="mb-3"
            />
            <div class="flex justify-end">
              <el-button type="primary" @click="submitComment" :loading="commentLoading">发表评论</el-button>
            </div>
          </div>

          <div class="space-y-6">
            <div v-for="(comment, index) in detail.comments" :key="index" class="border p-4 rounded">
              <div class="flex justify-between items-start mb-2">
                <div class="flex items-center font-semibold text-gray-800">
                  <el-avatar :size="24" :src="comment.authorAvatar" class="mr-2 text-xs bg-blue-100 text-blue-600">{{ comment.author.charAt(0) }}</el-avatar>
                  {{ comment.author }}
                </div>
                <div class="text-xs text-gray-400">{{ comment.createTime }}</div>
              </div>
              <div class="text-gray-700 whitespace-pre-wrap">{{ comment.content }}</div>

              <div v-if="comment.attachments && comment.attachments.length > 0" class="mt-3 space-y-2">
                <div
                  v-for="file in comment.attachments"
                  :key="file.id"
                  class="flex items-center justify-between rounded-lg border border-blue-100 bg-blue-50/40 px-3 py-2 text-sm"
                >
                  <div class="flex min-w-0 items-center text-blue-700">
                    <el-icon class="mr-2 shrink-0"><Document /></el-icon>
                    <span class="truncate">{{ file.name }}</span>
                    <span class="ml-2 shrink-0 text-xs text-blue-400">({{ file.size }})</span>
                  </div>
                  <el-button size="small" type="primary" link @click="downloadFile(file)">下载</el-button>
                </div>
              </div>

              <div class="mt-3 flex items-center gap-2">
                <input
                  :ref="(el) => setCommentFileInput(comment.id, el)"
                  type="file"
                  class="hidden"
                  @change="handleCommentFileChange(comment, $event)"
                />
                <el-button size="small" plain :loading="uploadingCommentId === comment.id" @click="openCommentFilePicker(comment.id)">
                  <el-icon class="mr-1"><Paperclip /></el-icon>上传附件
                </el-button>
              </div>
              
              <!-- 二级回复 -->
              <div v-if="comment.replies && comment.replies.length > 0" class="mt-4 pl-4 border-l-2 border-gray-200 space-y-3 bg-gray-50 p-3 rounded">
                <div v-for="(reply, rIdx) in comment.replies" :key="rIdx" class="text-sm">
                   <div class="flex justify-between">
                     <span class="inline-flex items-center font-medium text-blue-800">
                       <el-avatar :size="18" :src="reply.authorAvatar" class="mr-1 text-[10px] bg-blue-100 text-blue-600">{{ reply.author.charAt(0) }}</el-avatar>
                       {{ reply.author }}
                     </span>
                     <span class="text-xs text-gray-400">{{ reply.createTime }}</span>
                   </div>
                   <div class="text-gray-600 mt-1">{{ reply.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getTopicDetail, addComment, downloadForumFile, uploadCommentFile, deleteTopic } from '@/api/modules/forum';
import { ArrowLeft, Reading, Clock, Paperclip, Document } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useUserStore } from '@/stores/user';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();

const detail = ref<any>(null);
const loading = ref(false);
const newComment = ref('');
const commentLoading = ref(false);
const uploadingCommentId = ref<number | null>(null);
const commentFileInputs = ref<Record<number, HTMLInputElement>>({});

const fetchData = async () => {
  loading.value = true;
  try {
    detail.value = await getTopicDetail(route.params.id as string);
  } finally {
    loading.value = false;
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

const handleCommentFileChange = async (comment: any, event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;

  uploadingCommentId.value = comment.id;
  try {
    const uploaded = await uploadCommentFile(route.params.id as string, comment.id, file);
    if (!comment.attachments) comment.attachments = [];
    comment.attachments.push(uploaded);
    ElMessage.success('评论附件上传成功');
  } catch (error: any) {
    ElMessage.error(error.message || '评论附件上传失败');
  } finally {
    uploadingCommentId.value = null;
  }
};

const submitComment = async () => {
  if (!newComment.value.trim()) {
    ElMessage.warning('评论内容不能为空');
    return;
  }
  commentLoading.value = true;
  try {
    const comment: any = await addComment(route.params.id as string, { content: newComment.value });
    detail.value.comments.unshift(comment || {
      id: Date.now(),
      author: userStore.userInfo?.name || '测试用户',
      content: newComment.value,
      createTime: '刚刚',
      replies: []
    });
    newComment.value = '';
    ElMessage.success('评论发表成功');
  } finally {
    commentLoading.value = false;
  }
}

const handleDeleteTopic = async () => {
  if (!detail.value) return;
  try {
    await ElMessageBox.confirm(`确定删除话题「${detail.value.title}」吗？`, '删除话题', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    });
    await deleteTopic(detail.value.id);
    ElMessage.success('话题已删除');
    router.push('/forum');
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除话题失败');
    }
  }
};

onMounted(() => {
  fetchData();
});
</script>
