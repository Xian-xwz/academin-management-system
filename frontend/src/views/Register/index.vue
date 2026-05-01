<template>
  <div class="h-screen bg-gray-100 flex items-center justify-center">
    <el-card class="w-full max-w-md p-6 shadow-lg">
      <div class="text-2xl font-bold text-center mb-6">系统注册</div>
      <el-form :model="regForm" :rules="rules" ref="regFormRef" label-width="80px" @keyup.enter="handleReg">
        <el-form-item label="学号" prop="studentId">
          <el-input v-model="regForm.studentId" placeholder="请输入学号" />
        </el-form-item>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="regForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="regForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="regForm.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="regForm.confirmPassword" type="password" placeholder="请再次输入密码" show-password />
        </el-form-item>
        <el-button type="primary" class="w-full mt-2" size="large" :loading="loading" @click="handleReg">注 册</el-button>
        <div class="mt-4 text-sm text-center text-gray-500">
          已有账号？ <router-link to="/login" class="text-blue-500 hover:underline">去登录</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { register } from '@/api/modules/auth';
import { ElMessage, type FormInstance, type FormRules } from 'element-plus';

const router = useRouter();
const regFormRef = ref<FormInstance>();
const regForm = ref({
  studentId: '',
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
});
const loading = ref(false);

const validatePass2 = (rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入密码'));
  } else if (value !== regForm.value.password) {
    callback(new Error('两次输入密码不一致!'));
  } else {
    callback();
  }
};

const rules: FormRules = {
  studentId: [{ required: true, message: '请输入学号', trigger: 'blur' }],
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: ['blur', 'change'] }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, validator: validatePass2, trigger: 'blur' }
  ]
};

const handleReg = async () => {
  if (!regFormRef.value) return;
  await regFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        await register(regForm.value);
        ElMessage.success('注册成功，请登录');
        router.push('/login');
      } catch (error: any) {
        ElMessage.error(error.message || '注册失败');
      } finally {
        loading.value = false;
      }
    }
  });
};
</script>
