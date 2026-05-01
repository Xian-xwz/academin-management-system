<template>
  <el-upload
    class="upload-demo"
    action="#"
    :auto-upload="false"
    :on-change="handleChange"
    :on-remove="handleRemove"
    :file-list="fileList"
    multiple
  >
    <el-button type="primary">选择附件 (Mock)</el-button>
    <template #tip>
      <div class="el-upload__tip text-gray-500 mt-2">
        当前为 Mock 阶段，仅展示上传交互，不会真实上传文件。支持大小不超过 50MB。
      </div>
    </template>
  </el-upload>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const fileList = ref<any[]>([]);

const handleChange = (file: any, files: any[]) => {
  fileList.value = files;
};
const handleRemove = (file: any, files: any[]) => {
  fileList.value = files;
};
</script>
