<template>
  <div class="bg-white rounded p-6 shadow-sm max-w-4xl mx-auto">
    <h2 class="text-2xl font-bold mb-6 text-gray-800 border-b pb-4">{{ isEditMode ? '编辑话题' : '发布新话题' }}</h2>
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px" label-position="top">
      <el-form-item label="话题标题" prop="title">
        <el-input v-model="form.title" placeholder="请输入话题标题，简明扼要说明主题" size="large" />
      </el-form-item>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <el-form-item label="所属专业" prop="major">
          <el-select v-model="form.major" placeholder="请选择专业" class="w-full">
            <el-option v-for="major in majors" :key="major.code" :label="major.name" :value="major.name" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="话题标签 (回车添加自定义)" prop="tags">
          <el-select
            v-model="form.tags"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="请选择或输入标签"
            class="w-full"
          >
            <el-option label="提问求助" value="提问求助" />
            <el-option label="复习资料" value="复习资料" />
            <el-option label="考研交流" value="考研交流" />
            <el-option label="实习选排" value="实习选排" />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item label="话题内容" prop="content">
        <el-input 
          v-model="form.content" 
          type="textarea" 
          :rows="12" 
          placeholder="请输入详细内容，支持 Markdown 格式（演示阶段仅限文本）..." 
        />
      </el-form-item>

      <el-form-item label="附加资料上传">
        <el-upload
          action="#"
          :auto-upload="false"
          :file-list="fileList"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
          multiple
        >
          <el-button type="primary" plain>选择附件</el-button>
          <template #tip>
            <div class="el-upload__tip text-gray-500 mt-2">
              附件会在确认发布后上传到后端，单文件大小不超过 50MB。
            </div>
          </template>
        </el-upload>
      </el-form-item>

      <div class="flex justify-end space-x-4 mt-8 border-t pt-4">
        <el-button @click="$router.back()">取消并返回</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="loading" size="large" class="w-32">{{ isEditMode ? '保存修改' : '确认发布' }}</el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage, type FormInstance } from 'element-plus';
import type { UploadUserFile } from 'element-plus';
import { createTopic, getForumMajors, getTopicDetail, updateTopic, uploadTopicFile } from '@/api/modules/forum';

const router = useRouter();
const route = useRoute();
const formRef = ref<FormInstance>();
const loading = ref(false);
const fileList = ref<UploadUserFile[]>([]);
const majors = ref<Array<{ code: string; name: string }>>([]);
const isEditMode = computed(() => Boolean(route.params.id));

const form = ref({ 
  title: '', 
  major: '',
  tags: [] as string[],
  content: '' 
});

const rules = {
  title: [{ required: true, message: '请填写标题', trigger: 'blur' }],
  content: [{ required: true, message: '请填写详细内容', trigger: 'blur' }],
  major: [{ required: true, message: '请选择相关专业', trigger: 'change' }]
};

const handleFileChange = (_file: UploadUserFile, files: UploadUserFile[]) => {
  fileList.value = files;
};

const handleFileRemove = (_file: UploadUserFile, files: UploadUserFile[]) => {
  fileList.value = files;
};

const fetchMajors = async () => {
  try {
    majors.value = await getForumMajors();
  } catch (error: any) {
    ElMessage.warning(error.message || '专业列表加载失败');
  }
};

const loadTopic = async () => {
  if (!isEditMode.value) return;
  loading.value = true;
  try {
    const detail: any = await getTopicDetail(route.params.id as string);
    form.value = {
      title: detail.title || '',
      major: detail.major || '',
      tags: detail.tags || [],
      content: detail.content || ''
    };
  } finally {
    loading.value = false;
  }
};

const uploadPendingFiles = async (topicId: string | number) => {
  const files = fileList.value
    .map(file => file.raw)
    .filter((file): file is File => file instanceof File);
  for (const file of files) {
    await uploadTopicFile(topicId, file);
  }
};

const handleSubmit = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        const topic: any = isEditMode.value
          ? await updateTopic(route.params.id as string, form.value)
          : await createTopic(form.value);
        await uploadPendingFiles(topic.id);
        ElMessage.success(isEditMode.value ? '话题修改成功！' : '发布话题成功！');
        router.push(`/forum/topics/${topic.id}`);
      } catch (e: any) {
        ElMessage.error(e.message || (isEditMode.value ? '修改失败' : '发布失败'));
      } finally {
        loading.value = false;
      }
    }
  });
};

onMounted(() => {
  fetchMajors();
  loadTopic();
});
</script>
