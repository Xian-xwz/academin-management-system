<template>
  <div class="mx-auto max-w-6xl space-y-6">
    <div class="rounded-3xl border border-blue-100 bg-gradient-to-r from-slate-900 to-blue-900 p-7 text-white shadow-sm">
      <div class="text-sm text-blue-200">Teaching Affairs Workbench</div>
      <h1 class="mt-2 text-2xl font-bold">教务工作台</h1>
      <p class="mt-3 max-w-2xl text-sm leading-relaxed text-blue-100">
        面向教务管理员的只读管理入口，用于查看用户账号、穿透学生毕业进度，并验证管理员权限边界。
      </p>
    </div>

    <el-skeleton :loading="loading" animated>
      <template #template>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
          <el-skeleton-item v-for="item in 4" :key="item" variant="rect" style="height: 120px; border-radius: 18px;" />
        </div>
      </template>
      <template #default>
        <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
          <div v-for="card in metricCards" :key="card.label" class="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
            <div class="flex items-center justify-between">
              <span class="text-sm text-slate-500">{{ card.label }}</span>
              <div class="flex h-9 w-9 items-center justify-center rounded-xl" :class="card.iconClass">
                <el-icon><component :is="card.icon" /></el-icon>
              </div>
            </div>
            <div class="mt-5 text-3xl font-bold text-slate-900">{{ card.value }}</div>
            <div class="mt-1 text-xs text-slate-400">{{ card.desc }}</div>
          </div>
        </div>
      </template>
    </el-skeleton>

    <div class="grid grid-cols-1 gap-5 lg:grid-cols-3">
      <div class="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm lg:col-span-2">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h2 class="text-lg font-bold text-slate-900">专业学生分布</h2>
            <p class="mt-1 text-sm text-slate-400">按学生账号绑定专业统计，不包含管理员账号。</p>
          </div>
        </div>
        <div v-if="summary?.majorDistribution?.length" class="space-y-4">
          <div v-for="major in summary.majorDistribution" :key="major.majorCode || major.majorName || 'empty'">
            <div class="mb-1 flex justify-between text-sm">
              <span class="font-medium text-slate-700">{{ major.majorName || '未绑定专业' }}</span>
              <span class="text-slate-400">{{ major.count }} 人</span>
            </div>
            <el-progress :percentage="majorPercent(major.count)" :show-text="false" :stroke-width="8" />
          </div>
        </div>
        <el-empty v-else description="暂无专业分布数据" />
      </div>

      <div class="rounded-2xl border border-slate-100 bg-white p-6 shadow-sm">
        <h2 class="text-lg font-bold text-slate-900">快捷入口</h2>
        <div class="mt-5 space-y-3">
          <button class="w-full rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-left transition hover:border-blue-200 hover:bg-blue-100" @click="router.push('/admin/users')">
            <div class="font-semibold text-blue-700">查看用户与毕业进度</div>
            <div class="mt-1 text-xs text-blue-500">按学号、专业、角色筛选账号</div>
          </button>
          <button class="w-full rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-left transition hover:border-amber-200 hover:bg-amber-100" @click="router.push('/admin/forum')">
            <div class="font-semibold text-amber-700">论坛内容治理</div>
            <div class="mt-1 text-xs text-amber-600">隐藏学生端违规帖子</div>
          </button>
          <button class="w-full rounded-xl border border-slate-100 px-4 py-3 text-left transition hover:border-slate-200 hover:bg-slate-50" @click="router.push('/dashboard')">
            <div class="font-semibold text-slate-700">返回学生端首页</div>
            <div class="mt-1 text-xs text-slate-400">核对学生视角展示效果</div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { CircleCheck, User, UserFilled, Warning } from '@element-plus/icons-vue';
import { AdminDashboardSummary, getAdminDashboardSummary } from '@/api/modules/admin';

const router = useRouter();
const loading = ref(false);
const summary = ref<AdminDashboardSummary | null>(null);

const metricCards = computed(() => [
  { label: '总用户数', value: summary.value?.totalUsers || 0, desc: '系统内全部账号', icon: UserFilled, iconClass: 'bg-blue-50 text-blue-500' },
  { label: '学生账号', value: summary.value?.studentUsers || 0, desc: '参与学业数据统计', icon: User, iconClass: 'bg-emerald-50 text-emerald-500' },
  { label: '管理员', value: summary.value?.adminUsers || 0, desc: '可访问教务工作台', icon: Warning, iconClass: 'bg-amber-50 text-amber-500' },
  { label: '启用账号', value: summary.value?.activeUsers || 0, desc: '当前可登录账号', icon: CircleCheck, iconClass: 'bg-indigo-50 text-indigo-500' },
]);

const majorPercent = (count: number) => {
  const total = summary.value?.studentUsers || 0;
  return total > 0 ? Math.round((count / total) * 100) : 0;
};

const fetchSummary = async () => {
  loading.value = true;
  try {
    summary.value = await getAdminDashboardSummary();
  } catch (error: any) {
    ElMessage.error(error.message || '管理员摘要加载失败');
  } finally {
    loading.value = false;
  }
};

onMounted(fetchSummary);
</script>
