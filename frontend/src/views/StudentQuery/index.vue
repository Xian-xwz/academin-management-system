<template>
  <div class="max-w-5xl mx-auto space-y-6">
    <div class="bg-white p-6 rounded shadow-sm">
      <h2 class="text-2xl font-bold mb-2 text-gray-800">学号查询</h2>
      <p class="text-gray-500 mb-6">请输入学号以检索学生的毕业要求、已修课程及还需要修读的学分建议等学业信息。</p>
      
      <div class="flex space-x-2">
        <el-input 
          v-model="studentId" 
          placeholder="请输入 8-20 位学号 (模拟演示可任意输入)" 
          class="max-w-md" 
          clearable
          @keyup.enter="handleQuery"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" @click="handleQuery" :loading="loading">查 询</el-button>
      </div>
      <div v-if="errorMsg" class="mt-2 text-red-500 text-sm">{{ errorMsg }}</div>
    </div>
    
    <div v-loading="loading">
      <AcademicInfoCard v-if="result" :data="result" />
      <el-empty v-else-if="searched && !loading && !result" description="未查到该学号的信息，请确认学号是否正确" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { getAcademicInfo } from '@/api/modules/student';
import { isValidStudentId } from '@/utils/validate';
import AcademicInfoCard from '@/components/AcademicInfoCard/index.vue';
import { Search } from '@element-plus/icons-vue';

const studentId = ref('');
const loading = ref(false);
const result = ref<any>(null);
const searched = ref(false);
const errorMsg = ref('');

const handleQuery = async () => {
  errorMsg.value = '';
  if (!studentId.value) {
    errorMsg.value = '学号不能为空';
    return;
  }
  if (!isValidStudentId(studentId.value)) {
    errorMsg.value = '请输入有效的学号（8-20位数字或字母）';
    return;
  }
  
  loading.value = true;
  searched.value = true;
  result.value = null;
  
  try {
    const res = await getAcademicInfo(studentId.value);
    result.value = res;
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};
</script>
