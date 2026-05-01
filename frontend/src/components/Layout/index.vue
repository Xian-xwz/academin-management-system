<template>
  <div class="layout-wrapper flex h-screen overflow-hidden bg-gray-100 transition-colors">
    <!-- 左侧侧边栏 (PC端) -->
    <aside 
      class="bg-white border-r flex-col hidden sm:flex relative shrink-0 transition-colors"
      :style="{ width: sidebarWidth + 'px' }"
    >
      <!-- 拖拽调节宽度的把手 -->
      <div
        class="absolute top-0 -right-1 w-2 h-full cursor-col-resize z-50 hover:bg-blue-400 transition-colors select-none"
        :class="{ 'bg-blue-400': isDragging }"
        @mousedown.prevent="startDrag"
      ></div>
      
      <div class="h-16 flex items-center justify-center border-b font-bold text-gray-800 tracking-wider shrink-0 overflow-hidden whitespace-nowrap transition-colors">
        学业管理系统
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="flex-1 w-full border-r-0"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataBoard /></el-icon>
          <template #title>工作台首页</template>
        </el-menu-item>
        <el-menu-item index="/student-query">
          <el-icon><Search /></el-icon>
          <template #title>学号查询</template>
        </el-menu-item>
        <el-menu-item index="/schedule">
          <el-icon><Calendar /></el-icon>
          <template #title>我的课表</template>
        </el-menu-item>
        <el-menu-item index="/time-plan">
          <el-icon><Clock /></el-icon>
          <template #title>时间规划</template>
        </el-menu-item>
        <el-menu-item index="/forum">
          <el-icon><ChatLineRound /></el-icon>
          <template #title>交流论坛</template>
        </el-menu-item>
        <el-menu-item index="/ai-chat">
          <el-icon><Service /></el-icon>
          <template #title>AI 问询</template>
        </el-menu-item>
        <el-menu-item v-if="userStore.userInfo?.role === 'admin'" index="/admin">
          <el-icon><DataBoard /></el-icon>
          <template #title>返回教务工作台</template>
        </el-menu-item>
      </el-menu>
    </aside>

    <!-- 移动端侧边抽屉 -->
    <el-drawer
      v-model="mobileMenuOpen"
      direction="ltr"
      size="240px"
      :with-header="false"
      class="sm:hidden"
    >
      <div class="h-16 flex items-center justify-center border-b font-bold text-gray-800 tracking-wider transition-colors">
        学业管理系统
      </div>
      <el-menu
        :default-active="$route.path"
        router
        class="border-r-0"
        @select="mobileMenuOpen = false"
      >
        <el-menu-item index="/dashboard"><el-icon><DataBoard /></el-icon> 工作台首页</el-menu-item>
        <el-menu-item index="/student-query"><el-icon><Search /></el-icon> 学号查询</el-menu-item>
        <el-menu-item index="/schedule"><el-icon><Calendar /></el-icon> 我的课表</el-menu-item>
        <el-menu-item index="/time-plan"><el-icon><Clock /></el-icon> 时间规划</el-menu-item>
        <el-menu-item index="/forum"><el-icon><ChatLineRound /></el-icon> 交流论坛</el-menu-item>
        <el-menu-item index="/ai-chat"><el-icon><Service /></el-icon> AI 问询</el-menu-item>
        <el-menu-item v-if="userStore.userInfo?.role === 'admin'" index="/admin"><el-icon><DataBoard /></el-icon> 返回教务工作台</el-menu-item>
      </el-menu>
    </el-drawer>

    <!-- 右侧内容 -->
    <div class="flex-1 flex flex-col h-screen overflow-hidden relative">
      <!-- 顶部导航 -->
      <header class="h-16 bg-white border-b flex items-center justify-between px-4 sm:px-6 transition-colors">
        <div class="flex items-center">
          <el-icon class="text-2xl cursor-pointer mr-3 sm:hidden text-gray-700" @click="mobileMenuOpen = true">
            <Expand />
          </el-icon>
          <div class="text-xl font-semibold sm:hidden text-gray-800">
            学业管理系统
          </div>
        </div>
        
        <div class="flex items-center space-x-4 ml-auto">
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="el-dropdown-link cursor-pointer flex items-center text-gray-700">
              {{ userStore.userInfo?.name || '用户' }} <el-icon class="ml-1"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="userStore.userInfo?.role === 'admin'" command="admin">教务工作台</el-dropdown-item>
                <el-dropdown-item command="profile">个人主页</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 主要内容区域 -->
      <main class="flex-1 overflow-y-auto p-4 md:p-6 bg-gray-50 transition-colors">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useUserStore } from '@/stores/user';
import { DataBoard, Search, Calendar, Clock, ChatLineRound, Service, ArrowDown, Expand } from '@element-plus/icons-vue';

const router = useRouter();
const userStore = useUserStore();
const mobileMenuOpen = ref(false);

// 侧边栏拖拽可调宽度逻辑
const sidebarWidth = ref(256); // 默认 256px = 16rem = tailwind 的 w-64
const isDragging = ref(false);

onMounted(() => {
  const savedWidth = localStorage.getItem('sidebarWidth');
  if (savedWidth) {
    sidebarWidth.value = parseInt(savedWidth, 10);
  }
});

watch(sidebarWidth, (val) => {
  localStorage.setItem('sidebarWidth', val.toString());
});

const startDrag = (e: MouseEvent) => {
  isDragging.value = true;
  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
  document.addEventListener('mousemove', onDrag);
  document.addEventListener('mouseup', stopDrag);
};

const onDrag = (e: MouseEvent) => {
  if (!isDragging.value) return;
  let newWidth = e.clientX;
  if (newWidth < 200) newWidth = 200; // 最小宽度
  if (newWidth > 600) newWidth = 600; // 最大宽度
  sidebarWidth.value = newWidth;
};

const stopDrag = () => {
  if (isDragging.value) {
    isDragging.value = false;
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    document.removeEventListener('mousemove', onDrag);
    document.removeEventListener('mouseup', stopDrag);
  }
};

onUnmounted(() => {
  document.removeEventListener('mousemove', onDrag);
  document.removeEventListener('mouseup', stopDrag);
});

const handleCommand = (command: string) => {
  if (command === 'logout') {
    userStore.logout();
    router.push('/login');
  } else if (command === 'profile') {
    router.push('/profile');
  } else if (command === 'admin') {
    router.push('/admin');
  }
};
</script>

<style scoped>
.el-menu {
  border-right: none;
}
</style>
