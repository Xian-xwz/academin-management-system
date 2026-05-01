<template>
  <div class="h-screen bg-gray-100 flex items-center justify-center">
    <el-card class="w-full max-w-md p-6 shadow-lg">
      <div class="text-2xl font-bold text-center mb-6">基于AI的学业管理系统</div>
      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" @keyup.enter="handleLogin">
        <el-form-item prop="username">
          <el-input v-model="loginForm.username" placeholder="请输入学号/用户名" size="large">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="loginForm.password" type="password" placeholder="请输入密码" size="large" show-password>
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" class="w-full" size="large" :loading="loading" @click="handleLogin">登 录</el-button>
        <div class="mt-4 text-sm text-center text-gray-500">
          还没账号？ <router-link to="/register" class="text-blue-500 hover:underline">去注册</router-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { login } from '@/api/modules/auth';
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus';
import { User, Lock } from '@element-plus/icons-vue';

const router = useRouter();
const userStore = useUserStore();

const loginFormRef = ref<FormInstance>();
const loginForm = ref({ username: '', password: '' });
const loading = ref(false);

const rules: FormRules = {
  username: [
    { required: true, message: '学号/用户名不能为空', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '密码不能为空', trigger: 'blur' }
  ]
};

const handleLogin = async () => {
  if (!loginFormRef.value) return;
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true;
      try {
        const res: any = await login(loginForm.value);
        userStore.loginSubmit(res.token);
        userStore.setUserInfo(res.userInfo);
        ElMessage.success('登录成功');
        const warnings = Array.isArray(res.pendingAcademicWarnings) ? res.pendingAcademicWarnings : [];
        if (warnings.length && res.userInfo?.role === 'student') {
          await ElMessageBox.alert(formatAcademicWarnings(warnings), '学业预警提醒', {
            confirmButtonText: '我知道了',
            type: 'warning',
          });
        }
        const redirect = router.currentRoute.value.query.redirect as string | undefined;
        router.push(redirect || (res.userInfo?.role === 'admin' ? '/admin' : '/dashboard'));
      } catch (error: any) {
        ElMessage.error(error.message || '登录失败，请检查账号密码');
      } finally {
        loading.value = false;
      }
    }
  });
};

const formatAcademicWarnings = (warnings: Array<{ title?: string; content?: string }>) => {
  if (warnings.length === 1) {
    const warning = warnings[0];
    return `${warning.title || '学业预警提醒'}\n\n${warning.content || ''}`;
  }
  return warnings
    .map((warning, index) => `${index + 1}. ${warning.title || '学业预警提醒'}\n${warning.content || ''}`)
    .join('\n\n');
};
</script>
