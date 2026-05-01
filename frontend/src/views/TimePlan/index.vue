<template>
  <div class="bg-white rounded p-6 shadow-sm space-y-6">
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center">
      <h2 class="text-2xl font-bold text-gray-800">时间规划</h2>
      <div class="mt-4 md:mt-0 space-x-3 flex items-center">
        <el-radio-group v-model="viewMode">
          <el-radio-button label="list">列表视图</el-radio-button>
          <el-radio-button label="calendar">日历视图</el-radio-button>
        </el-radio-group>
        <el-button type="success" plain @click="handleSync" :loading="syncing">从课表同步</el-button>
        <el-button type="primary" @click="openDialog()">新增事件</el-button>
      </div>
    </div>

    <!-- 列表视图 -->
    <div v-if="viewMode === 'list'" v-loading="loading">
      <el-table :data="events" style="width: 100%">
        <el-table-column label="事件标题" min-width="150" prop="title" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.type)">{{ row.type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="280">
          <template #default="{ row }">
            {{ row.startTime }} <span v-if="row.endTime">至 {{ row.endTime }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-select v-model="row.status" size="small" class="w-24" @change="handleStatusChange(row)">
              <el-option label="待开始" value="待开始" />
              <el-option label="进行中" value="进行中" />
              <el-option label="已完成" value="已完成" />
              <el-option label="已结束" value="已结束" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 日历视图 -->
    <div v-if="viewMode === 'calendar'" v-loading="loading">
      <Calendar :events="events" @day-click="handleDayClick" />
    </div>

    <!-- 表单弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑事件' : '新增事件'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="事件标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入标题" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-select v-model="form.type" placeholder="选择类型" class="w-full">
            <el-option label="课程" value="课程" />
            <el-option label="考试" value="考试" />
            <el-option label="作业" value="作业" />
            <el-option label="个人" value="个人" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围" prop="timeRange">
          <el-date-picker
            v-model="form.timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm"
            class="w-full"
          />
        </el-form-item>
        <el-form-item label="地点" prop="location">
          <el-input v-model="form.location" placeholder="选填，例如：图书馆" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" placeholder="选择状态" class="w-full">
            <el-option label="待开始" value="待开始" />
            <el-option label="进行中" value="进行中" />
            <el-option label="已完成" value="已完成" />
            <el-option label="已结束" value="已结束" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述" prop="desc">
          <el-input v-model="form.desc" type="textarea" :rows="3" placeholder="选填，描述详情记录" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm" :loading="saving">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { getTimePlans, addTimePlan, updateTimePlan, deleteTimePlan, syncFromSchedule } from '@/api/modules/timePlan';
import Calendar from '@/components/Calendar/index.vue';
import { ElMessage, ElMessageBox, type FormInstance } from 'element-plus';

const events = ref<any[]>([]);
const loading = ref(false);
const syncing = ref(false);

const viewMode = ref('list');

// Dialog values
const dialogVisible = ref(false);
const formRef = ref<FormInstance>();
const saving = ref(false);
const form = ref<any>({});

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  timeRange: [{ required: true, message: '请选择时间范围', trigger: 'change' }],
};

const getTypeTag = (type: string) => {
  switch(type) {
    case '课程': return 'info';
    case '考试': return 'danger';
    case '作业': return 'warning';
    case '个人': return 'success';
    default: return '';
  }
};

const fetchEvents = async () => {
  loading.value = true;
  try {
    events.value = await getTimePlans() as any;
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchEvents();
});

const handleSync = async () => {
  syncing.value = true;
  try {
    const res: any = await syncFromSchedule();
    ElMessage.success(`从课表同步了 ${res.synced ?? 0} 个事件`);
    fetchEvents();
  } finally {
    syncing.value = false;
  }
};

const openDialog = (row?: any) => {
  if (row) {
    form.value = { ...row, timeRange: [row.startTime, row.endTime] };
  } else {
    form.value = { title: '', type: '个人', timeRange: [], location: '', desc: '', status: '待开始' };
  }
  dialogVisible.value = true;
};

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true;
      try {
        const payload = {
          ...form.value,
          startTime: form.value.timeRange && form.value.timeRange[0],
          endTime: form.value.timeRange && form.value.timeRange[1]
        };
        
        if (form.value.id) {
          await updateTimePlan(form.value.id, payload);
          ElMessage.success('更新事件成功');
        } else {
          await addTimePlan(payload);
          ElMessage.success('新增事件成功');
        }
        dialogVisible.value = false;
        fetchEvents();
      } finally {
        saving.value = false;
      }
    }
  });
};

const handleDelete = (id: number) => {
  ElMessageBox.confirm('确定要删除该规划事件吗？', '提示', { type: 'warning' }).then(async () => {
    await deleteTimePlan(id);
    ElMessage.success('删除成功');
    fetchEvents();
  }).catch(() => {});
};

const handleStatusChange = async (row: any) => {
  try {
    await updateTimePlan(row.id, { status: row.status });
    ElMessage.success('事件状态已更新');
  } catch (error: any) {
    ElMessage.error(error.message || '状态更新失败');
    fetchEvents();
  }
};

const handleDayClick = (date: Date) => {
  // If user clicks a day in calendar, open dialog to add event on that day.
  const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  form.value = { title: '', type: '个人', timeRange: [`${dateStr} 08:00`, `${dateStr} 09:00`], location: '', desc: '', status: '待开始' };
  dialogVisible.value = true;
};
</script>
