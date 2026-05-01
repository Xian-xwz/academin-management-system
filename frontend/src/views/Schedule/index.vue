<template>
  <div class="bg-white rounded p-6 shadow-sm space-y-6">
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center">
      <h2 class="text-2xl font-bold text-gray-800">课程表查询</h2>
      
      <div class="flex flex-wrap gap-3 mt-4 md:mt-0">
        <el-select v-model="currentTerm" class="w-40" @change="fetchData">
          <el-option label="2025-2026 第一学期" value="2025-2026-1" />
          <el-option label="2023-2024 第一学期" value="2023-2024-1" />
          <el-option label="2022-2023 第二学期" value="2022-2023-2" />
        </el-select>
        
        <el-select v-model="currentWeek" class="w-32" @change="fetchData">
          <el-option v-for="w in 20" :key="w" :label="`第 ${w} 周`" :value="w" />
        </el-select>
        
        <el-input v-model="searchKeyword" placeholder="搜索课程/教师" class="w-48" clearable>
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </div>
    </div>

    <!-- 课表网格 -->
    <div v-loading="loading" class="mt-4">
      <ScheduleGrid v-if="filteredCourses.length > 0" :courses="filteredCourses" @edit-note="handleEditNote"/>
      <el-empty v-else description="本周没有排课哦，适当放松一下吧" />
    </div>

    <!-- 备注编辑弹窗 -->
    <el-dialog v-model="dialogVisible" title="课程备注编辑" width="400px">
      <div v-if="selectedCourse" class="mb-4 text-sm text-gray-600 bg-gray-50 p-3 rounded">
        <div><strong>课程：</strong>{{ selectedCourse.name }}</div>
        <div><strong>时间：</strong>周{{ selectedCourse.day }} 第{{ selectedCourse.sections.join(',') }}节</div>
        <div><strong>地点：</strong>{{ selectedCourse.location }}</div>
      </div>
      <el-input
        v-model="editNoteText"
        type="textarea"
        :rows="4"
        placeholder="记录课堂注意事项、期末画重点提醒..."
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="danger" plain @click="handleClearNote">清空</el-button>
          <el-button type="primary" @click="handleSaveNote" :loading="saving">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { getSchedule, updateCourseNote } from '@/api/modules/schedule';
import ScheduleGrid from '@/components/ScheduleGrid/index.vue';
import { Search } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';

const scheduleData = ref<any[]>([]);
const loading = ref(false);

const currentTerm = ref('2025-2026-1');
const currentWeek = ref(5);
const searchKeyword = ref('');

const dialogVisible = ref(false);
const selectedCourse = ref<any>(null);
const editNoteText = ref('');
const saving = ref(false);

const fetchData = async () => {
  loading.value = true;
  try {
    const res: any = await getSchedule({ term: currentTerm.value, week: currentWeek.value });
    scheduleData.value = res.courses || [];
  } finally {
    loading.value = false;
  }
};

const filteredCourses = computed(() => {
  if (!searchKeyword.value) return scheduleData.value;
  const kw = searchKeyword.value.toLowerCase();
  return scheduleData.value.filter(c => 
    (c.name || '').toLowerCase().includes(kw) || 
    (c.teacher || '').toLowerCase().includes(kw) || 
    (c.location || '').toLowerCase().includes(kw)
  );
});

onMounted(() => {
  fetchData();
});

const handleEditNote = (course: any) => {
  selectedCourse.value = course;
  editNoteText.value = course.note || '';
  dialogVisible.value = true;
};

const handleSaveNote = async () => {
  if (!selectedCourse.value) return;
  saving.value = true;
  try {
    await updateCourseNote(selectedCourse.value.id, editNoteText.value);
    
    // update locally for mock
    const idx = scheduleData.value.findIndex(c => c.id === selectedCourse.value.id);
    if (idx !== -1) {
      scheduleData.value[idx].note = editNoteText.value;
    }
    
    ElMessage.success('备注保存成功');
    dialogVisible.value = false;
  } finally {
    saving.value = false;
  }
};

const handleClearNote = () => {
  editNoteText.value = '';
  handleSaveNote();
};
</script>
