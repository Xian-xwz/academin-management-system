<template>
  <div class="flex h-screen overflow-hidden bg-slate-100">
    <aside class="hidden w-64 shrink-0 border-r border-slate-200 bg-slate-950 text-white md:flex md:flex-col">
      <div class="flex h-16 items-center border-b border-white/10 px-6">
        <div>
          <div class="text-lg font-bold tracking-wide">教务工作台</div>
          <div class="text-xs text-slate-400">Academic Admin Console</div>
        </div>
      </div>

      <el-menu
        :default-active="$route.path"
        router
        background-color="#020617"
        text-color="#cbd5e1"
        active-text-color="#60a5fa"
        class="admin-menu flex-1 border-r-0"
      >
        <el-menu-item index="/admin">
          <el-icon><DataBoard /></el-icon>
          <template #title>工作台概览</template>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><UserFilled /></el-icon>
          <template #title>用户与进度</template>
        </el-menu-item>
        <el-menu-item index="/admin/forum">
          <el-icon><ChatLineRound /></el-icon>
          <template #title>论坛治理</template>
        </el-menu-item>
      </el-menu>
    </aside>

    <el-drawer v-model="mobileMenuOpen" direction="ltr" size="240px" :with-header="false" class="md:hidden">
      <div class="flex h-16 items-center border-b px-5 font-bold text-slate-900">教务工作台</div>
      <el-menu :default-active="$route.path" router class="border-r-0" @select="mobileMenuOpen = false">
        <el-menu-item index="/admin"><el-icon><DataBoard /></el-icon> 工作台概览</el-menu-item>
        <el-menu-item index="/admin/users"><el-icon><UserFilled /></el-icon> 用户与进度</el-menu-item>
        <el-menu-item index="/admin/forum"><el-icon><ChatLineRound /></el-icon> 论坛治理</el-menu-item>
      </el-menu>
    </el-drawer>

    <div class="flex min-w-0 flex-1 flex-col">
      <header class="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6">
        <div class="flex items-center">
          <el-icon class="mr-3 cursor-pointer text-2xl text-slate-700 md:hidden" @click="mobileMenuOpen = true">
            <Expand />
          </el-icon>
          <div>
            <div class="text-sm text-slate-400">管理员端</div>
            <div class="font-semibold text-slate-800">{{ pageTitle }}</div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <el-button size="small" plain @click="router.push('/dashboard')">返回学生端</el-button>
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="flex cursor-pointer items-center text-sm text-slate-700">
              {{ userStore.userInfo?.name || '管理员' }}
              <el-icon class="ml-1"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人主页</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto p-4 md:p-6">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { ArrowDown, ChatLineRound, DataBoard, Expand, UserFilled } from '@element-plus/icons-vue';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const mobileMenuOpen = ref(false);

const pageTitle = computed(() => {
  if (route.path.startsWith('/admin/users/') && route.path.endsWith('/progress')) return '学生毕业进度';
  if (route.path.startsWith('/admin/users')) return '用户与账号';
  if (route.path.startsWith('/admin/forum')) return '论坛治理';
  return '工作台概览';
});

const handleCommand = (command: string) => {
  if (command === 'logout') {
    userStore.logout();
    router.push('/login');
  } else if (command === 'profile') {
    router.push('/profile');
  }
};
</script>

<style scoped>
.admin-menu {
  border-right: none;
}
</style>
