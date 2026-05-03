<template>
  <div class="knowledge-page mx-auto max-w-7xl pb-10">
    <div class="mb-6 flex flex-col gap-4 rounded-3xl bg-gradient-to-r from-slate-900 via-blue-900 to-indigo-800 p-6 text-white shadow-sm md:flex-row md:items-end md:justify-between">
      <div>
        <div class="text-sm text-blue-100">Knowledge Gallery</div>
        <h2 class="mt-1 text-2xl font-bold">知识卡片画廊</h2>
        <p class="mt-2 max-w-2xl text-sm leading-6 text-blue-50">
          输入知识文本或上传参考图片，由 Dify 工作流自动理解内容、选择模板并生成可下载的知识卡片。
        </p>
      </div>
      <el-button type="primary" size="large" round @click="openCreateDrawer">
        <el-icon class="mr-1"><Plus /></el-icon>
        新建卡片
      </el-button>
    </div>

    <div class="mb-5 flex flex-col gap-3 rounded-2xl bg-white p-4 shadow-sm md:flex-row md:items-center">
      <el-input v-model="query" clearable placeholder="搜索标题或输入内容" class="md:max-w-xs" @keyup.enter="loadCards(1)">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="statusFilter" clearable placeholder="全部状态" class="md:w-40" @change="loadCards(1)">
        <el-option label="生成成功" value="succeeded" />
        <el-option label="生成中" value="processing" />
        <el-option label="生成失败" value="failed" />
      </el-select>
      <div class="flex flex-1 justify-end gap-2">
        <el-button @click="loadCards(1)">刷新</el-button>
        <el-button type="primary" @click="openCreateDrawer">生成新卡片</el-button>
      </div>
    </div>

    <el-skeleton :loading="loading" animated :count="6">
      <template #template>
        <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <div v-for="n in 6" :key="n" class="rounded-2xl bg-white p-4 shadow-sm">
            <el-skeleton-item variant="image" style="width: 100%; height: 220px; border-radius: 16px" />
            <el-skeleton-item variant="h3" style="width: 70%; margin-top: 16px" />
            <el-skeleton-item variant="text" style="width: 40%; margin-top: 8px" />
          </div>
        </div>
      </template>
      <template #default>
        <el-empty v-if="!cards.length" description="暂无知识卡片，先生成第一张吧">
          <el-button type="primary" @click="openCreateDrawer">新建卡片</el-button>
        </el-empty>
        <div v-else class="gallery-grid">
          <div
            v-for="card in cards"
            :key="card.id"
            class="gallery-card group overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100 transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <div class="relative aspect-[4/3] bg-slate-100">
              <img
                v-if="cardImageUrls[card.id]"
                :src="cardImageUrls[card.id]"
                loading="lazy"
                decoding="async"
                class="h-full w-full object-cover"
                :alt="card.title || '知识卡片'"
              />
              <div v-else class="flex h-full items-center justify-center text-slate-400">
                <el-icon class="text-5xl"><Picture /></el-icon>
              </div>
              <div class="absolute left-3 top-3">
                <el-tag :type="statusTagType(card.status)" effect="dark">{{ statusText(card.status) }}</el-tag>
              </div>
            </div>
            <div class="p-4">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <h3 class="truncate text-base font-semibold text-slate-900">{{ card.title || '未命名卡片' }}</h3>
                  <p class="mt-1 text-xs text-slate-400">{{ formatTime(card.createdAt) }}</p>
                </div>
                <el-tag v-if="card.imageNumber" size="small" type="info">#{{ card.imageNumber }}</el-tag>
              </div>
              <p v-if="card.routeReason" class="mt-3 line-clamp-2 text-sm text-slate-500">{{ card.routeReason }}</p>
              <p v-if="card.errorMessage" class="mt-3 line-clamp-2 text-sm text-red-500">{{ card.errorMessage }}</p>
              <div class="mt-4 flex items-center justify-between gap-2">
                <el-button link type="primary" @click="openDetail(card.id)">查看详情</el-button>
                <div class="flex items-center gap-1">
                  <el-button link :disabled="!cardImageUrls[card.id]" @click="downloadImage(card)">下载</el-button>
                  <el-button link type="danger" @click="deleteCard(card)">删除</el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-if="total > pageSize" class="mt-6 flex justify-center">
          <el-pagination
            background
            layout="prev, pager, next"
            :total="total"
            :page-size="pageSize"
            :current-page="page"
            @current-change="loadCards"
          />
        </div>
      </template>
    </el-skeleton>

    <el-drawer v-model="drawerVisible" size="min(520px, 100vw)" title="新建知识卡片" destroy-on-close>
      <div class="space-y-5">
        <el-alert
          title="系统会自动选择模板和风格，用户无需手动挑选。"
          type="info"
          :closable="false"
          show-icon
        />
        <el-form label-position="top">
          <el-form-item label="知识内容">
            <el-input
              v-model="createForm.inputText"
              type="textarea"
              :rows="8"
              maxlength="3000"
              show-word-limit
              placeholder="粘贴知识点、概念解释、复习提纲或课堂笔记..."
              :disabled="generating"
            />
          </el-form-item>
          <el-form-item label="参考图片（可选）">
            <el-upload
              drag
              action="#"
              :auto-upload="false"
              :limit="1"
              :file-list="fileList"
              accept="image/png,image/jpeg,image/webp"
              :on-change="handleFileChange"
              :on-remove="handleFileRemove"
              :disabled="generating"
            >
              <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
              <div class="el-upload__text">拖拽图片到这里，或 <em>点击上传</em></div>
              <template #tip>
                <div class="text-xs text-slate-400">支持 jpg、png、webp，最大 10MB。</div>
              </template>
            </el-upload>
          </el-form-item>
          <el-form-item label="补充要求（可选）">
            <el-input
              v-model="createForm.extraPrompt"
              type="textarea"
              :rows="3"
              maxlength="500"
              show-word-limit
              placeholder="例如：突出考试重点、适合手机阅读、偏学术风..."
              :disabled="generating"
            />
          </el-form-item>
        </el-form>

        <div v-if="streamMessages.length" class="rounded-2xl bg-slate-50 p-4">
          <div class="mb-3 flex items-center justify-between">
            <span class="text-sm font-medium text-slate-700">生成进度</span>
            <el-tag v-if="currentGeneratingCardId" size="small">ID {{ currentGeneratingCardId }}</el-tag>
          </div>
          <div class="space-y-2">
            <div v-for="(message, index) in streamMessages" :key="index" class="flex items-start text-sm text-slate-600">
              <el-icon class="mr-2 mt-0.5 text-blue-500"><Loading v-if="generating && index === streamMessages.length - 1" /><CircleCheck v-else /></el-icon>
              <span>{{ message }}</span>
            </div>
          </div>
        </div>

        <div v-if="previewUrl" class="rounded-2xl border border-blue-100 bg-blue-50 p-3">
          <img :src="previewUrl" class="max-h-[360px] w-full rounded-xl object-contain bg-white" alt="生成预览" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button :disabled="generating" @click="drawerVisible = false">关闭</el-button>
          <el-button type="primary" :loading="generating" @click="submitCreate">开始生成</el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="detailVisible" title="知识卡片详情" width="min(860px, 94vw)">
      <div v-if="detail" class="grid gap-5 md:grid-cols-[1.1fr_0.9fr]">
        <div class="rounded-2xl bg-slate-50 p-3">
          <img
            v-if="detailImageUrl"
            :src="detailImageUrl"
            class="max-h-[520px] w-full rounded-xl object-contain bg-white"
            alt="知识卡片详情"
          />
          <el-empty v-else description="暂无输出图片" />
        </div>
        <div class="space-y-4">
          <div>
            <div class="text-xs text-slate-400">标题</div>
            <div class="mt-1 font-semibold text-slate-900">{{ detail.title || '未命名卡片' }}</div>
          </div>
          <div>
            <div class="text-xs text-slate-400">生成状态</div>
            <el-tag class="mt-1" :type="statusTagType(detail.status)">{{ statusText(detail.status) }}</el-tag>
          </div>
          <div v-if="detail.inputText">
            <div class="text-xs text-slate-400">原始内容</div>
            <p class="mt-1 max-h-32 overflow-y-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-sm text-slate-700">{{ detail.inputText }}</p>
          </div>
          <div v-if="detail.prompt">
            <div class="text-xs text-slate-400">最终 Prompt</div>
            <p class="mt-1 max-h-40 overflow-y-auto whitespace-pre-wrap rounded-xl bg-slate-50 p-3 text-sm text-slate-700">{{ detail.prompt }}</p>
          </div>
          <div v-if="detail.routeReason">
            <div class="text-xs text-slate-400">自动路由说明</div>
            <p class="mt-1 text-sm text-slate-700">{{ detail.routeReason }}</p>
          </div>
          <div class="flex gap-2">
            <el-button type="primary" :disabled="!detailImageUrl" @click="downloadImage(detail)">下载图片</el-button>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { UploadFile, UploadUserFile } from 'element-plus';
import { CircleCheck, Loading, Picture, Plus, Search, UploadFilled } from '@element-plus/icons-vue';
import {
  deleteKnowledgeCard,
  generateKnowledgeCardStream,
  getKnowledgeCard,
  getKnowledgeCards,
  loadKnowledgeCardImage
} from '@/api/modules/knowledgeCard';
import { KnowledgeCardDetail, KnowledgeCardItem } from '@/types/knowledgeCard';

const cards = ref<KnowledgeCardItem[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 18;
const query = ref('');
const statusFilter = ref('');
const loading = ref(false);
const drawerVisible = ref(false);
const generating = ref(false);
const streamMessages = ref<string[]>([]);
const currentGeneratingCardId = ref<number>();
const previewUrl = ref('');
const detailVisible = ref(false);
const detail = ref<KnowledgeCardDetail>();
const detailImageUrl = ref('');
const fileList = ref<UploadUserFile[]>([]);
const selectedImage = ref<File | null>(null);
const cardImageUrls = reactive<Record<number, string>>({});
let imageLoadVersion = 0;

const createForm = reactive({
  inputText: '',
  extraPrompt: ''
});

onMounted(() => {
  loadCards();
});

onBeforeUnmount(() => {
  revokeObjectUrls();
});

const revokeObjectUrls = () => {
  revokeDetailImageUrl();
  Object.values(cardImageUrls).forEach(url => URL.revokeObjectURL(url));
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
};

const revokeDetailImageUrl = () => {
  if (detailImageUrl.value && !Object.values(cardImageUrls).includes(detailImageUrl.value)) {
    URL.revokeObjectURL(detailImageUrl.value);
  }
  detailImageUrl.value = '';
};

const loadCards = async (targetPage = page.value) => {
  loading.value = true;
  const currentVersion = ++imageLoadVersion;
  try {
    page.value = targetPage;
    const data = await getKnowledgeCards({
      page: page.value,
      pageSize,
      q: query.value || undefined,
      status: statusFilter.value || undefined
    });
    cards.value = data.items;
    total.value = data.total;
    void loadCardImages(data.items, currentVersion);
  } finally {
    loading.value = false;
  }
};

const loadCardImages = async (items: KnowledgeCardItem[], version = imageLoadVersion) => {
  const targets = items.filter(card => card.outputImageUrl && !cardImageUrls[card.id]);
  const concurrency = 4;
  let cursor = 0;

  const worker = async () => {
    while (cursor < targets.length) {
      const card = targets[cursor++];
      if (version !== imageLoadVersion) return;
      if (!card.outputImageUrl || cardImageUrls[card.id]) continue;
      try {
        const imageUrl = await loadKnowledgeCardImage(card.outputImageUrl);
        if (version === imageLoadVersion) {
          cardImageUrls[card.id] = imageUrl;
        } else {
          URL.revokeObjectURL(imageUrl);
        }
      } catch {
        // 图片加载失败不阻断画廊列表。
      }
    }
  };

  await Promise.all(Array.from({ length: Math.min(concurrency, targets.length) }, worker));
};

const openCreateDrawer = () => {
  drawerVisible.value = true;
  streamMessages.value = [];
  currentGeneratingCardId.value = undefined;
  previewUrl.value = '';
};

const handleFileChange = (file: UploadFile) => {
  selectedImage.value = file.raw || null;
  fileList.value = file.raw ? [file] : [];
};

const handleFileRemove = () => {
  selectedImage.value = null;
  fileList.value = [];
};

const submitCreate = async () => {
  if (!createForm.inputText.trim() && !selectedImage.value) {
    ElMessage.warning('请输入知识内容或上传图片');
    return;
  }
  generating.value = true;
  streamMessages.value = [];
  previewUrl.value = '';
  try {
    await generateKnowledgeCardStream(
      {
        inputText: createForm.inputText,
        extraPrompt: createForm.extraPrompt,
        image: selectedImage.value
      },
      {
        onStatus: (message, cardId) => pushStreamMessage(message, cardId),
        onWorkflow: (message, _node, cardId) => pushStreamMessage(message, cardId),
        onPreview: async (imageUrl, cardId) => {
          if (cardId) currentGeneratingCardId.value = cardId;
          previewUrl.value = await loadKnowledgeCardImage(imageUrl);
        },
        onDone: async (card) => {
          currentGeneratingCardId.value = card.id;
          ElMessage.success('知识卡片生成完成');
          await loadCards(1);
          createForm.inputText = '';
          createForm.extraPrompt = '';
          selectedImage.value = null;
          fileList.value = [];
        },
        onError: (message, cardId) => {
          if (cardId) currentGeneratingCardId.value = cardId;
          ElMessage.error(message);
        }
      }
    );
  } finally {
    generating.value = false;
  }
};

const pushStreamMessage = (message: string, cardId?: number) => {
  if (cardId) currentGeneratingCardId.value = cardId;
  if (message && streamMessages.value[streamMessages.value.length - 1] !== message) {
    streamMessages.value.push(message);
  }
};

const openDetail = async (id: number) => {
  detail.value = await getKnowledgeCard(id);
  detailVisible.value = true;
  revokeDetailImageUrl();
  if (cardImageUrls[id]) {
    detailImageUrl.value = cardImageUrls[id];
    return;
  }
  if (detail.value.outputImageUrl) {
    try {
      const imageUrl = await loadKnowledgeCardImage(detail.value.outputImageUrl);
      cardImageUrls[id] = imageUrl;
      detailImageUrl.value = imageUrl;
    } catch {
      ElMessage.warning('详情图片加载失败，请刷新画廊后重试');
    }
  }
};

const downloadImage = (card: KnowledgeCardItem | KnowledgeCardDetail) => {
  const imageUrl = cardImageUrls[card.id] || detailImageUrl.value || previewUrl.value;
  if (!imageUrl) return;
  const link = document.createElement('a');
  link.href = imageUrl;
  link.download = `${card.title || 'knowledge-card'}-${card.id}.png`;
  link.click();
};

const deleteCard = async (card: KnowledgeCardItem) => {
  try {
    await ElMessageBox.confirm(
      `确认删除「${card.title || '未命名卡片'}」吗？删除后将同时清理已保存的图片。`,
      '删除知识卡片',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger'
      }
    );
  } catch {
    return;
  }

  await deleteKnowledgeCard(card.id);
  if (cardImageUrls[card.id]) {
    URL.revokeObjectURL(cardImageUrls[card.id]);
    delete cardImageUrls[card.id];
  }
  if (detail.value?.id === card.id) {
    detailVisible.value = false;
    detail.value = undefined;
    revokeDetailImageUrl();
  }
  ElMessage.success('知识卡片已删除');
  const nextPage = cards.value.length === 1 && page.value > 1 ? page.value - 1 : page.value;
  await loadCards(nextPage);
};

const statusText = (status: string) => {
  if (status === 'succeeded') return '已完成';
  if (status === 'failed') return '失败';
  return '生成中';
};

const statusTagType = (status: string) => {
  if (status === 'succeeded') return 'success';
  if (status === 'failed') return 'danger';
  return 'warning';
};

const formatTime = (value: string) => new Date(value).toLocaleString();
</script>

<style scoped>
.gallery-grid {
  column-count: 1;
  column-gap: 1rem;
}

.gallery-card {
  break-inside: avoid;
  margin-bottom: 1rem;
}

@media (min-width: 640px) {
  .gallery-grid {
    column-count: 2;
  }
}

@media (min-width: 1280px) {
  .gallery-grid {
    column-count: 3;
  }
}
</style>
