<template>
  <div class="mx-auto max-w-6xl space-y-5">
    <div class="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <div class="mb-4 flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div>
          <h1 class="text-xl font-bold text-slate-900">论坛治理</h1>
          <p class="mt-1 text-sm text-slate-400">查看学生帖子，支持隐藏（软删除）与取消隐藏恢复展示。</p>
        </div>
        <el-button type="primary" @click="fetchTopics">刷新列表</el-button>
      </div>
      <div class="grid grid-cols-1 gap-3 md:grid-cols-4">
        <el-input v-model="query.q" clearable placeholder="搜索标题/正文" @keyup.enter="handleSearch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="query.status" clearable placeholder="帖子状态">
          <el-option label="正常" value="normal" />
          <el-option label="已隐藏" value="deleted" />
        </el-select>
        <el-button type="primary" @click="handleSearch">查询</el-button>
        <el-button @click="resetSearch">重置</el-button>
      </div>
    </div>

    <div class="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <el-table v-loading="loading" :data="topics" stripe style="width: 100%">
        <el-table-column prop="title" label="帖子标题" min-width="240" show-overflow-tooltip />
        <el-table-column label="作者" min-width="160">
          <template #default="{ row }">
            <div class="font-medium text-slate-800">{{ row.author }}</div>
            <div class="text-xs text-slate-400">{{ row.authorStudentId }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="majorName" label="专业" min-width="150">
          <template #default="{ row }">{{ row.majorName || '未绑定' }}</template>
        </el-table-column>
        <el-table-column label="互动" width="160">
          <template #default="{ row }">
            <span class="text-xs text-slate-500">浏览 {{ row.views }} / 赞 {{ row.likes }} / 评 {{ row.comments }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'normal' ? 'success' : 'info'" effect="plain">
              {{ row.status === 'normal' ? '正常' : '已隐藏' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发布时间" width="170">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="router.push(`/forum/topics/${row.id}`)">查看</el-button>
            <el-button size="small" link type="danger" :disabled="row.status !== 'normal'" @click="hideTopic(row)">隐藏</el-button>
            <el-button size="small" link type="success" :disabled="row.status !== 'deleted'" @click="restoreTopic(row)">取消隐藏</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="mt-4 flex justify-end">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="fetchTopics"
          @size-change="handleSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Search } from '@element-plus/icons-vue';
import { AdminForumTopicItem, getAdminForumTopics, hideAdminForumTopic, patchAdminForumTopicStatus } from '@/api/modules/admin';

const router = useRouter();
const loading = ref(false);
const topics = ref<AdminForumTopicItem[]>([]);
const total = ref(0);

const query = reactive({
  page: 1,
  pageSize: 10,
  q: '',
  status: 'normal',
});

const formatDate = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const fetchTopics = async () => {
  loading.value = true;
  try {
    const res = await getAdminForumTopics({
      page: query.page,
      pageSize: query.pageSize,
      q: query.q || undefined,
      status: query.status || undefined,
    });
    topics.value = res.items;
    total.value = res.total;
  } catch (error: any) {
    ElMessage.error(error.message || '论坛帖子加载失败');
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  query.page = 1;
  fetchTopics();
};

const resetSearch = () => {
  query.page = 1;
  query.q = '';
  query.status = 'normal';
  fetchTopics();
};

const handleSizeChange = () => {
  query.page = 1;
  fetchTopics();
};

const hideTopic = async (row: AdminForumTopicItem) => {
  try {
    await ElMessageBox.confirm(`确定隐藏帖子「${row.title}」吗？隐藏后学生端论坛列表将不再展示。`, '隐藏帖子', {
      type: 'warning',
      confirmButtonText: '隐藏',
      cancelButtonText: '取消',
    });
    await hideAdminForumTopic(row.id);
    row.status = 'deleted';
    ElMessage.success('帖子已隐藏');
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '隐藏帖子失败');
    }
  }
};

const restoreTopic = async (row: AdminForumTopicItem) => {
  try {
    await ElMessageBox.confirm(`确定取消隐藏帖子「${row.title}」吗？恢复后学生端论坛列表将重新展示。`, '取消隐藏', {
      type: 'warning',
      confirmButtonText: '恢复展示',
      cancelButtonText: '取消',
    });
    await patchAdminForumTopicStatus(row.id, { status: 'normal' });
    row.status = 'normal';
    ElMessage.success('帖子已恢复展示');
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '取消隐藏失败');
    }
  }
};

onMounted(fetchTopics);
</script>
