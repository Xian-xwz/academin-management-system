<template>
  <div class="mx-auto max-w-6xl space-y-5">
    <div class="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <div class="mb-4 flex flex-col justify-between gap-3 md:flex-row md:items-center">
        <div>
          <h1 class="text-xl font-bold text-slate-900">用户与账号管理</h1>
          <p class="mt-1 text-sm text-slate-400">按学号、姓名、角色和启用状态筛选账号，并穿透查看学生毕业进度。</p>
        </div>
        <el-button type="primary" @click="fetchUsers">刷新列表</el-button>
      </div>

      <div class="grid grid-cols-1 gap-3 md:grid-cols-4">
        <el-input v-model="query.q" clearable placeholder="搜索学号/姓名" @keyup.enter="handleSearch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="query.role" clearable placeholder="角色">
          <el-option label="学生" value="student" />
          <el-option label="管理员" value="admin" />
        </el-select>
        <el-select v-model="query.isActive" clearable placeholder="启用状态">
          <el-option label="启用" :value="true" />
          <el-option label="停用" :value="false" />
        </el-select>
        <div class="flex gap-2">
          <el-button type="primary" class="flex-1" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </div>
      </div>
    </div>

    <div class="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
      <el-table v-loading="loading" :data="users" stripe style="width: 100%">
        <el-table-column label="用户" min-width="220">
          <template #default="{ row }">
            <div class="flex items-center">
              <el-avatar :size="36" :src="row.avatarUrl" class="mr-3 bg-blue-100 text-blue-600">{{ row.name.charAt(0) }}</el-avatar>
              <div>
                <div class="font-semibold text-slate-800">{{ row.name }}</div>
                <div class="text-xs text-slate-400">{{ row.studentId }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="majorName" label="专业" min-width="160">
          <template #default="{ row }">{{ row.majorName || '未绑定' }}</template>
        </el-table-column>
        <el-table-column prop="grade" label="年级" width="100">
          <template #default="{ row }">{{ row.grade || '-' }}</template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'warning' : 'success'" effect="light">
              {{ row.role === 'admin' ? '管理员' : '学生' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="isActive" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.isActive ? 'success' : 'info'" effect="plain">
              {{ row.isActive ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="170">
          <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button size="small" link type="primary" :disabled="row.role !== 'student'" @click="router.push(`/admin/users/${row.studentId}/progress`)">
              查看进度
            </el-button>
            <el-button size="small" link type="warning" :disabled="row.role !== 'student'" @click="openWarningDialog(row)">
              发预警
            </el-button>
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
          @current-change="fetchUsers"
          @size-change="handleSizeChange"
        />
      </div>
    </div>

    <el-drawer v-model="detailVisible" title="用户详情" size="420px">
      <div v-if="detail" class="space-y-4">
        <div class="flex items-center rounded-2xl bg-slate-50 p-4">
          <el-avatar :size="52" :src="detail.avatarUrl" class="mr-4 bg-blue-100 text-xl text-blue-600">{{ detail.name.charAt(0) }}</el-avatar>
          <div>
            <div class="text-lg font-bold text-slate-900">{{ detail.name }}</div>
            <div class="text-sm text-slate-400">{{ detail.studentId }}</div>
          </div>
        </div>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户名">{{ detail.username }}</el-descriptions-item>
          <el-descriptions-item label="专业">{{ detail.majorName || '未绑定' }}</el-descriptions-item>
          <el-descriptions-item label="年级">{{ detail.grade || '-' }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ detail.role === 'admin' ? '管理员' : '学生' }}</el-descriptions-item>
          <el-descriptions-item label="邮箱">{{ detail.email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ detail.isActive ? '启用' : '停用' }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(detail.updatedAt) }}</el-descriptions-item>
        </el-descriptions>
        <el-button v-if="detail.role === 'student'" type="primary" class="w-full" @click="router.push(`/admin/users/${detail.studentId}/progress`)">
          查看该生毕业进度
        </el-button>
        <el-button v-if="detail.role === 'student'" type="warning" plain class="w-full" @click="openWarningDialog(detail)">
          发送学业预警
        </el-button>
      </div>
    </el-drawer>

    <el-dialog v-model="warningVisible" title="发送学业预警" width="520px">
      <div v-if="warningTarget" class="mb-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-700">
        预警将发送给：{{ warningTarget.name }}（{{ warningTarget.studentId }}），学生下次登录时会看到一次弹窗。
      </div>
      <el-form label-position="top">
        <el-form-item label="预警标题">
          <el-input v-model="warningForm.title" maxlength="60" show-word-limit />
        </el-form-item>
        <el-form-item label="预警内容">
          <el-input v-model="warningForm.content" type="textarea" :rows="4" maxlength="300" show-word-limit placeholder="例如：当前实践教学学分缺口较大，请尽快确认毕业设计与实习环节安排。" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="warningVisible = false">取消</el-button>
        <el-button type="warning" :loading="warningSending" @click="sendWarning">发送预警</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Search } from '@element-plus/icons-vue';
import { AdminUserDetail, AdminUserItem, getAdminUserDetail, getAdminUsers, sendAdminAcademicWarning } from '@/api/modules/admin';

const router = useRouter();
const loading = ref(false);
const users = ref<AdminUserItem[]>([]);
const total = ref(0);
const detailVisible = ref(false);
const detail = ref<AdminUserDetail | null>(null);
const warningVisible = ref(false);
const warningSending = ref(false);
const warningTarget = ref<AdminUserItem | AdminUserDetail | null>(null);
const warningForm = reactive({
  title: '学业预警提醒',
  content: '',
});

const query = reactive<{
  page: number;
  pageSize: number;
  q: string;
  role: string;
  isActive?: boolean;
}>({
  page: 1,
  pageSize: 10,
  q: '',
  role: '',
  isActive: undefined,
});

const formatDate = (value?: string) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const fetchUsers = async () => {
  loading.value = true;
  try {
    const res = await getAdminUsers({
      page: query.page,
      pageSize: query.pageSize,
      q: query.q || undefined,
      role: query.role || undefined,
      isActive: query.isActive,
    });
    users.value = res.items;
    total.value = res.total;
  } catch (error: any) {
    ElMessage.error(error.message || '用户列表加载失败');
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  query.page = 1;
  fetchUsers();
};

const resetSearch = () => {
  query.page = 1;
  query.q = '';
  query.role = '';
  query.isActive = undefined;
  fetchUsers();
};

const handleSizeChange = () => {
  query.page = 1;
  fetchUsers();
};

const openDetail = async (row: AdminUserItem) => {
  try {
    detail.value = await getAdminUserDetail(row.studentId);
    detailVisible.value = true;
  } catch (error: any) {
    ElMessage.error(error.message || '用户详情加载失败');
  }
};

const openWarningDialog = (row: AdminUserItem | AdminUserDetail) => {
  warningTarget.value = row;
  warningForm.title = '学业预警提醒';
  warningForm.content = '';
  warningVisible.value = true;
};

const sendWarning = async () => {
  if (!warningTarget.value) return;
  if (!warningForm.content.trim()) {
    ElMessage.warning('请填写预警内容');
    return;
  }
  warningSending.value = true;
  try {
    await sendAdminAcademicWarning(warningTarget.value.studentId, {
      title: warningForm.title,
      content: warningForm.content,
    });
    warningVisible.value = false;
    ElMessage.success('学业预警已发送');
  } catch (error: any) {
    ElMessage.error(error.message || '学业预警发送失败');
  } finally {
    warningSending.value = false;
  }
};

onMounted(fetchUsers);
</script>
