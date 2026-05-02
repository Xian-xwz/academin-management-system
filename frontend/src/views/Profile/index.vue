<template>
  <div class="max-w-4xl mx-auto pb-10">
    <div class="mb-6">
      <h2 class="text-2xl font-bold text-gray-800">个人主页</h2>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- 基本信息卡片 -->
      <div class="md:col-span-1 border border-gray-100 shadow-sm rounded-2xl bg-white p-6 flex flex-col items-center transition-colors">
        <div class="relative group cursor-pointer mb-4" @click="openAvatarPicker">
          <el-avatar :size="100" :src="avatarUrl" class="bg-blue-100 text-blue-600 text-3xl font-bold">
            {{ userStore.userInfo?.name?.charAt(0) || 'U' }}
          </el-avatar>
          <div class="absolute inset-0 bg-black bg-opacity-50 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <el-icon class="text-white text-xl"><Camera /></el-icon>
          </div>
          <input ref="avatarInputRef" type="file" accept="image/*" class="hidden" @change="handleAvatarChange" />
        </div>
        <el-button size="small" type="primary" link :loading="avatarUploading" @click="openAvatarPicker">
          上传头像
        </el-button>
        <h3 class="text-xl font-bold text-gray-800">{{ userStore.userInfo?.name || '管理员' }}</h3>
        <p class="text-gray-500 text-sm mt-1">{{ userStore.userInfo?.role === 'admin' ? '系统管理员' : '学生' }}</p>

        <div class="w-full mt-6 space-y-4">
          <div class="flex items-center justify-between py-2 border-b border-gray-50">
             <span class="text-gray-500 text-sm"><el-icon class="mr-1.5"><Setting /></el-icon>状态</span>
             <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
               在校
             </span>
          </div>
          <div class="flex items-center justify-between py-2 border-b border-gray-50">
             <span class="text-gray-500 text-sm"><el-icon class="mr-1.5"><Trophy /></el-icon>排名</span>
             <span class="text-gray-800 text-sm font-medium">12 / 120</span>
          </div>
        </div>
      </div>

      <!-- 详细信息与设置 -->
      <div class="md:col-span-2 border border-gray-100 shadow-sm rounded-2xl bg-white overflow-hidden transition-colors">
        <el-tabs v-model="activeTab" class="px-6 pt-4 profile-tabs">
          <el-tab-pane label="学业档案" name="profile">
            <div class="py-4 space-y-6">
              <el-form label-position="top">
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
                  <el-form-item label="姓名">
                    <el-input :model-value="userStore.userInfo?.name" disabled />
                  </el-form-item>
                  <el-form-item label="学号">
                    <el-input :model-value="userStore.userInfo?.studentId" disabled />
                  </el-form-item>
                  <el-form-item label="学院">
                    <el-input model-value="电子与信息工程学院" disabled />
                  </el-form-item>
                  <el-form-item label="专业">
                    <el-input :model-value="userStore.userInfo?.majorName" disabled />
                  </el-form-item>
                  <el-form-item label="班级">
                    <el-input :model-value="className" disabled />
                  </el-form-item>
                  <el-form-item label="入学年份">
                    <el-input :model-value="entryYear" disabled />
                  </el-form-item>
                </div>
              </el-form>
              
              <div class="pt-4 border-t border-gray-100">
                <el-button type="primary" plain @click="passwordDialogVisible = true">修改密码</el-button>
              </div>
            </div>
          </el-tab-pane>
          
          <el-tab-pane label="系统外观" name="appearance">
            <div class="py-4 space-y-6">
              <div>
                <h4 class="text-sm font-medium text-gray-800 mb-3">主题强调色</h4>
                <div class="flex items-center space-x-4">
                  <div 
                    v-for="color in themeColors" 
                    :key="color.value"
                    @click="changeThemeColor(color.value)"
                    class="w-8 h-8 rounded-full cursor-pointer flex items-center justify-center transition-transform hover:scale-110 shadow-sm"
                    :style="{ backgroundColor: color.value }"
                  >
                    <el-icon v-if="currentColor === color.value" class="text-white"><Check /></el-icon>
                  </div>
                  <el-color-picker v-model="currentColor" @change="changeThemeColor" />
                </div>
                <p class="text-xs text-gray-400 mt-2">选择您喜欢的主题色，它将应用于全局的按钮、选中状态等。此设置当前暂存在本地。</p>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="420px" destroy-on-close @closed="resetPasswordForm">
      <el-form ref="passwordFormRef" :model="passwordForm" :rules="passwordRules" label-position="top">
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password autocomplete="current-password" />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="passwordForm.newPassword" type="password" show-password autocomplete="new-password" />
          <div class="mt-1 text-xs text-gray-400">至少 8 位，需同时包含字母和数字；不要使用 123456 或学号。</div>
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password autocomplete="new-password" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="passwordSubmitting" @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="passwordSubmitting" @click="submitPasswordChange">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, onMounted } from 'vue';
import { useUserStore } from '@/stores/user';
import { Camera, Setting, Trophy, Check } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import { changePassword, uploadAvatar } from '@/api/modules/auth';

const userStore = useUserStore();
const activeTab = ref('profile');
const avatarInputRef = ref<HTMLInputElement | null>(null);
const avatarUploading = ref(false);
const passwordDialogVisible = ref(false);
const passwordSubmitting = ref(false);
const passwordFormRef = ref<FormInstance>();
const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

const avatarUrl = computed(() => userStore.userInfo?.avatarUrl || '');

const entryYear = computed(() => {
  const grade = userStore.userInfo?.grade || '';
  return grade ? grade.replace('级', '年') : '';
});

const className = computed(() => {
  const majorName = userStore.userInfo?.majorName || '';
  const year = userStore.userInfo?.grade?.replace('级', '') || '';
  return majorName && year ? `${majorName}${year}级演示班` : '';
});

const themeColors = [
  { name: '默认蓝', value: '#409EFF' },
  { name: '清新绿', value: '#67C23A' },
  { name: '警告橘', value: '#E6A23C' },
  { name: '危险红', value: '#F56C6C' },
  { name: '极客紫', value: '#722ed1' },
];

const currentColor = ref('#409EFF');

const passwordRules: FormRules = {
  oldPassword: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '新密码至少需要 8 位', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (!value) return callback();
        if (value.trim() !== value) return callback(new Error('密码首尾不能包含空格'));
        if (value === '123456') return callback(new Error('不能使用 123456 作为密码'));
        if (value === userStore.userInfo?.studentId) return callback(new Error('密码不能与学号相同'));
        if (/^\d+$/.test(value)) return callback(new Error('密码不能是纯数字'));
        if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) return callback(new Error('密码需同时包含字母和数字'));
        callback();
      },
      trigger: 'blur'
    }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== passwordForm.newPassword) return callback(new Error('两次输入的新密码不一致'));
        callback();
      },
      trigger: 'blur'
    }
  ]
};

const openAvatarPicker = () => {
  if (avatarUploading.value) return;
  avatarInputRef.value?.click();
};

const handleAvatarChange = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  if (!file.type.startsWith('image/')) {
    ElMessage.warning('请选择图片文件作为头像');
    return;
  }

  avatarUploading.value = true;
  try {
    const userInfo = await uploadAvatar(file);
    userStore.setUserInfo(userInfo);
    ElMessage.success('头像上传成功，论坛头像已同步');
  } catch (error: any) {
    ElMessage.error(error.message || '头像上传失败');
  } finally {
    avatarUploading.value = false;
  }
};

const resetPasswordForm = () => {
  passwordForm.oldPassword = '';
  passwordForm.newPassword = '';
  passwordForm.confirmPassword = '';
  passwordFormRef.value?.clearValidate();
};

const submitPasswordChange = async () => {
  if (!passwordFormRef.value) return;
  const valid = await passwordFormRef.value.validate().catch(() => false);
  if (!valid) return;

  passwordSubmitting.value = true;
  try {
    await changePassword({
      oldPassword: passwordForm.oldPassword,
      newPassword: passwordForm.newPassword
    });
    ElMessage.success('密码修改成功，请使用新密码登录');
    passwordDialogVisible.value = false;
    resetPasswordForm();
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.message || error.message || '密码修改失败');
  } finally {
    passwordSubmitting.value = false;
  }
};

const changeThemeColor = (color: string) => {
  if (!color) return;
  currentColor.value = color;
  const el = document.documentElement;
  
  // Update element plus theme css variables
  el.style.setProperty('--el-color-primary', color);
  
  // Calculate hover/active colors (simplified for mock)
  el.style.setProperty('--el-color-primary-light-3', shadeColor(color, 30));
  el.style.setProperty('--el-color-primary-light-5', shadeColor(color, 50));
  el.style.setProperty('--el-color-primary-light-7', shadeColor(color, 70));
  el.style.setProperty('--el-color-primary-light-9', shadeColor(color, 90));
  el.style.setProperty('--el-color-primary-dark-2', shadeColor(color, -20));
  
  // Update tailwind blue-500/600 etc approximation for our custom ui
  // Note: changing Tailwind CSS variables dynamically requires a custom setup if we use arbitrary classes,
  // but since we are mixing Element Plus and Tailwind, applying primary color to Element Plus takes care of the main UI elements.
  
  localStorage.setItem('theme-color', color);
};

// Extremely simple color shade function
function shadeColor(color: string, percent: number) {
  let R = parseInt(color.substring(1,3),16);
  let G = parseInt(color.substring(3,5),16);
  let B = parseInt(color.substring(5,7),16);

  R = parseInt(String(R * (100 + percent) / 100));
  G = parseInt(String(G * (100 + percent) / 100));
  B = parseInt(String(B * (100 + percent) / 100));

  R = (R<255)?R:255;  
  G = (G<255)?G:255;  
  B = (B<255)?B:255;  

  R = (R>0)?R:0;
  G = (G>0)?G:0;
  B = (B>0)?B:0;

  const RR = ((R.toString(16).length==1)?"0"+R.toString(16):R.toString(16));
  const GG = ((G.toString(16).length==1)?"0"+G.toString(16):G.toString(16));
  const BB = ((B.toString(16).length==1)?"0"+B.toString(16):B.toString(16));

  return "#"+RR+GG+BB;
}

onMounted(() => {
  const savedColor = localStorage.getItem('theme-color');
  if (savedColor) {
    currentColor.value = savedColor;
    changeThemeColor(savedColor);
  }
});
</script>

<style scoped>
:deep(.profile-tabs .el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
}
:deep(.profile-tabs .el-tabs__nav-wrap::after) {
  height: 1px;
  background-color: #f3f4f6;
}
</style>
