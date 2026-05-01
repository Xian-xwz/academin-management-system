<template>
  <div class="mx-auto max-w-5xl space-y-5">
    <div class="flex flex-col justify-between gap-3 rounded-2xl border border-slate-100 bg-white p-5 shadow-sm md:flex-row md:items-center">
      <div>
        <div class="text-sm text-slate-400">教务视角 · 只读</div>
        <h1 class="mt-1 text-xl font-bold text-slate-900">学生毕业进度</h1>
        <p class="mt-1 text-sm text-slate-500">当前查看学号：{{ studentId }}</p>
      </div>
      <div class="flex gap-2">
        <el-button @click="router.push('/admin/users')">返回用户列表</el-button>
        <el-button type="primary" :loading="loading" @click="fetchAcademicInfo">刷新进度</el-button>
      </div>
    </div>

    <div v-loading="loading">
      <AcademicInfoCard v-if="academicInfo" :data="academicInfo" />
      <el-empty v-else-if="!loading" description="暂无该学生学业信息" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import AcademicInfoCard from '@/components/AcademicInfoCard/index.vue';
import { getAdminUserAcademicInfo } from '@/api/modules/admin';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const academicInfo = ref<any>(null);
const studentId = computed(() => route.params.studentId as string);

const fetchAcademicInfo = async () => {
  if (!studentId.value) return;
  loading.value = true;
  try {
    academicInfo.value = await getAdminUserAcademicInfo(studentId.value);
  } catch (error: any) {
    academicInfo.value = null;
    ElMessage.error(error.message || '学生毕业进度加载失败');
  } finally {
    loading.value = false;
  }
};

onMounted(fetchAcademicInfo);
</script>
