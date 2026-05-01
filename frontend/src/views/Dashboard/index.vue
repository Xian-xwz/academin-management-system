<template>
  <div class="max-w-6xl mx-auto p-4 md:p-8">
    <!-- 头部欢迎区 -->
    <div class="mb-10 flex flex-col md:flex-row justify-between items-start md:items-center bg-gradient-to-r from-blue-50 to-white py-8 px-8 rounded-3xl border border-blue-100/60 shadow-sm relative overflow-hidden transition-colors">
      <!-- 装饰背景 -->
      <div class="absolute -right-10 -top-10 w-40 h-40 bg-blue-100/50 rounded-full blur-2xl"></div>
      <div class="absolute right-20 -bottom-10 w-32 h-32 bg-indigo-100/40 rounded-full blur-xl"></div>
      
      <div class="relative z-10">
        <h1 class="text-2xl md:text-3xl font-bold text-gray-800 tracking-tight">你好，欢迎使用 <span class="text-blue-600">AI 学业管理系统</span></h1>
        <p class="text-gray-500 mt-3 text-sm md:text-base max-w-xl leading-relaxed">基于大模型构建的数智化校园助手。在这里，您可以轻松追踪课业进度、获取学习资源，并体验专属 AI 答疑辅导。</p>
      </div>
    </div>

    <!-- 学业概览区 -->
    <div class="mb-12">
      <h2 class="text-lg font-semibold mb-5 text-gray-800 flex items-center">
        <span class="w-1.5 h-5 bg-blue-500 rounded-full mr-2"></span>
        学业概览
      </h2>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-5">
        
        <div class="col-span-2 bg-white p-5 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-300">
          <div class="flex items-center justify-between mb-3">
            <span class="text-gray-500 text-[13px] font-medium">毕业学分进度</span>
            <div class="w-7 h-7 rounded-full bg-blue-50 flex items-center justify-center">
              <el-icon class="text-blue-500"><Trophy /></el-icon>
            </div>
          </div>
          <div class="flex items-end justify-between mb-2">
            <div class="flex items-baseline space-x-1">
              <span class="text-2xl font-bold text-gray-800">{{ academicOverview.earned }}</span>
              <span class="text-xs text-gray-400">/ {{ academicOverview.total }} 分</span>
            </div>
            <span class="text-sm font-semibold text-blue-600">{{ academicOverview.percent }}%</span>
          </div>
          <el-progress :percentage="academicOverview.percent" :show-text="false" :stroke-width="8" color="#3b82f6" />
        </div>

        <div class="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-300">
          <div class="flex items-center justify-between mb-3">
            <span class="text-gray-500 text-[13px] font-medium">本期课程</span>
            <div class="w-7 h-7 rounded-full bg-blue-50 flex items-center justify-center">
              <el-icon class="text-blue-500"><Reading /></el-icon>
            </div>
          </div>
          <div class="flex items-baseline space-x-1">
            <span class="text-2xl font-bold text-gray-800">6</span>
            <span class="text-xs text-gray-400">门</span>
          </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md hover:-translate-y-1 transition-all duration-300">
          <div class="flex items-center justify-between mb-3">
            <span class="text-gray-500 text-[13px] font-medium">待办事项</span>
            <div class="w-7 h-7 rounded-full bg-blue-50 flex items-center justify-center">
              <el-icon class="text-blue-500"><Bell /></el-icon>
            </div>
          </div>
          <div class="flex items-baseline space-x-1">
            <span class="text-2xl font-bold text-gray-800">{{ pendingTodoCount }}</span>
            <span class="text-xs text-gray-400">项</span>
          </div>
        </div>

      </div>
    </div>

    <!-- 待办与消息区 -->
    <div class="mb-12 grid grid-cols-1 lg:grid-cols-2 gap-5">
      <!-- 待办事项 -->
      <div class="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col transition-colors">
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-lg font-semibold text-gray-800 flex items-center">
            <span class="w-1.5 h-5 bg-blue-500 rounded-full mr-2"></span>
            近期待办
          </h2>
          <el-button type="primary" link class="!text-xs" @click="$router.push('/time-plan')">查看全部</el-button>
        </div>
        <div class="space-y-4 flex-1 mt-1">
          <div v-for="todo in todos" :key="todo.id" class="flex items-start group cursor-pointer" @click="toggleTodo(todo)">
            <div class="h-5 flex items-center mr-3 mt-0.5" @click.stop>
              <el-checkbox :model-value="todo.completed" class="!h-auto !mr-0" @change="toggleTodo(todo)" />
            </div>
            <div class="flex-1 min-w-0">
              <div 
                class="text-sm font-medium transition-colors truncate"
                :class="todo.completed ? 'text-gray-400 line-through' : 'text-gray-800 group-hover:text-blue-600'"
              >
                {{ todo.title }}
              </div>
              <div class="text-xs mt-1.5 flex items-center" :class="todo.completed ? 'text-gray-400' : 'text-gray-400'">
                <template v-if="todo.completed">
                  <el-icon class="mr-1 text-green-500"><Select /></el-icon> <span class="text-green-600">已完成</span>
                </template>
                <template v-else>
                  <el-icon class="mr-1"><Clock /></el-icon> 截止：{{ todo.deadline }}
                  <span v-if="todo.highPriority" class="ml-3 px-1.5 py-0.5 bg-red-50 text-red-500 rounded text-[10px]">高优先级</span>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 消息通知 -->
      <div class="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm flex flex-col transition-colors">
        <div class="flex items-center justify-between mb-5">
          <h2 class="text-lg font-semibold text-gray-800 flex items-center">
            <span class="w-1.5 h-5 bg-blue-500 rounded-full mr-2"></span>
            消息通知
            <span v-if="unreadNotifications.length" class="ml-2 h-2 w-2 rounded-full bg-red-500 shadow-sm"></span>
          </h2>
          <el-button type="primary" link class="!text-xs" @click="markAllRead">标记已读</el-button>
        </div>
        <div class="space-y-4 flex-1">
          <div v-for="notice in visibleNotifications" :key="notice.id" class="flex items-start cursor-pointer group" @click="openNotification(notice)">
            <div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0 mr-3 transition-colors" :class="getNotificationClass(notice.type)">
              <el-icon v-if="notice.type === 'forum_comment'"><ChatLineRound /></el-icon>
              <el-icon v-else-if="notice.type === 'forum_like'"><Star /></el-icon>
              <el-icon v-else><Memo /></el-icon>
            </div>
            <div class="flex-1 min-w-0 border-b border-gray-50 pb-3">
              <div class="flex items-center justify-between">
                <div class="text-sm font-medium text-gray-800 truncate transition-colors" :class="{ 'text-gray-400': notice.read }">{{ notice.title }}</div>
                <div class="text-[11px] text-gray-400 shrink-0 ml-2">{{ formatRelativeTime(notice.time) }}</div>
              </div>
              <div class="text-xs text-gray-500 mt-1 truncate">{{ notice.content }}</div>
            </div>
          </div>
          <div v-if="unreadNotifications.length === 0" class="py-6 text-center text-sm text-gray-400">暂无新通知</div>
          <div v-if="unreadNotifications.length > collapsedNoticeCount" class="pt-1 text-center">
            <el-button link type="primary" class="!text-xs" @click="noticeExpanded = !noticeExpanded">
              {{ noticeExpanded ? '收起通知' : `展开全部 ${unreadNotifications.length} 条` }}
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 功能入口卡片 -->
    <div>
      <h2 class="text-lg font-semibold mb-5 text-gray-800 flex items-center">
        <span class="w-1.5 h-5 bg-blue-500 rounded-full mr-2"></span>
        快捷导航
      </h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        
        <div @click="$router.push('/student-query')" class="group bg-white p-5 rounded-3xl border border-gray-100 shadow-sm hover:shadow-lg hover:border-blue-200 transition-all cursor-pointer flex items-center">
          <div class="w-14 h-14 shrink-0 rounded-2xl bg-gray-50 group-hover:bg-blue-50 flex items-center justify-center mr-4 transition-colors">
            <el-icon class="text-2xl text-gray-400 group-hover:text-blue-500 transition-colors"><Search /></el-icon>
          </div>
          <div class="min-w-0">
            <div class="font-bold text-gray-800 group-hover:text-blue-600 transition-colors text-[15px]">学号查询</div>
            <div class="text-[13px] text-gray-500 mt-1 truncate">检索学生基础档案与成绩信息</div>
          </div>
        </div>

        <div @click="$router.push('/ai-chat')" class="group bg-white p-5 rounded-3xl border border-gray-100 shadow-sm hover:shadow-lg hover:border-blue-200 transition-all cursor-pointer flex items-center">
          <div class="w-14 h-14 shrink-0 rounded-2xl bg-gray-50 group-hover:bg-blue-50 flex items-center justify-center mr-4 transition-colors">
            <el-icon class="text-2xl text-gray-400 group-hover:text-blue-500 transition-colors"><Service /></el-icon>
          </div>
          <div class="min-w-0">
            <div class="font-bold text-gray-800 group-hover:text-blue-600 transition-colors text-[15px]">AI 问询</div>
            <div class="text-[13px] text-gray-500 mt-1 truncate">您的专属大模型学习得力助手</div>
          </div>
        </div>

        <div @click="$router.push('/forum')" class="group bg-white p-5 rounded-3xl border border-gray-100 shadow-sm hover:shadow-lg hover:border-blue-200 transition-all cursor-pointer flex items-center">
          <div class="w-14 h-14 shrink-0 rounded-2xl bg-gray-50 group-hover:bg-blue-50 flex items-center justify-center mr-4 transition-colors">
            <el-icon class="text-2xl text-gray-400 group-hover:text-blue-500 transition-colors"><ChatDotRound /></el-icon>
          </div>
          <div class="min-w-0">
            <div class="font-bold text-gray-800 group-hover:text-blue-600 transition-colors text-[15px]">交流论坛</div>
            <div class="text-[13px] text-gray-500 mt-1 truncate">探讨专业问题，分享复习笔记</div>
          </div>
        </div>

        <div @click="$router.push('/schedule')" class="group bg-white p-5 rounded-3xl border border-gray-100 shadow-sm hover:shadow-lg hover:border-blue-200 transition-all cursor-pointer flex items-center">
          <div class="w-14 h-14 shrink-0 rounded-2xl bg-gray-50 group-hover:bg-blue-50 flex items-center justify-center mr-4 transition-colors">
            <el-icon class="text-2xl text-gray-400 group-hover:text-blue-500 transition-colors"><Calendar /></el-icon>
          </div>
          <div class="min-w-0">
            <div class="font-bold text-gray-800 group-hover:text-blue-600 transition-colors text-[15px]">我的课表</div>
            <div class="text-[13px] text-gray-500 mt-1 truncate">查看本学期的每日课程安排</div>
          </div>
        </div>

        <div @click="$router.push('/time-plan')" class="group bg-white p-5 rounded-3xl border border-gray-100 shadow-sm hover:shadow-lg hover:border-blue-200 transition-all cursor-pointer flex items-center">
          <div class="w-14 h-14 shrink-0 rounded-2xl bg-gray-50 group-hover:bg-blue-50 flex items-center justify-center mr-4 transition-colors">
            <el-icon class="text-2xl text-gray-400 group-hover:text-blue-500 transition-colors"><Clock /></el-icon>
          </div>
          <div class="min-w-0">
            <div class="font-bold text-gray-800 group-hover:text-blue-600 transition-colors text-[15px]">时间规划</div>
            <div class="text-[13px] text-gray-500 mt-1 truncate">管理你的学习待办及考试倒计时</div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { Search, Service, ChatDotRound, Calendar, Clock, Trophy, Reading, Bell, Select, ChatLineRound, Star, Memo } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import { getTimePlans, updateTimePlan } from '@/api/modules/timePlan';
import { DashboardNotification, getDashboardNotifications } from '@/api/modules/dashboard';
import { useUserStore } from '@/stores/user';
import { getAcademicInfo } from '@/api/modules/student';

interface TodoItem {
  id: number;
  title: string;
  deadline: string;
  highPriority: boolean;
  completed: boolean;
  raw: any;
}

const router = useRouter();
const userStore = useUserStore();
const todos = ref<TodoItem[]>([]);
const notifications = ref<DashboardNotification[]>([]);
const readNotificationIds = ref<string[]>([]);
const noticeExpanded = ref(false);
const collapsedNoticeCount = 4;
const academicOverview = ref({
  earned: 0,
  total: 0,
  percent: 0
});

const pendingTodoCount = computed(() => todos.value.filter(todo => !todo.completed).length);
const readStorageKey = computed(() => `dashboard_read_notifications_${userStore.userInfo?.studentId || 'anonymous'}`);
const unreadNotifications = computed(() => notifications.value.filter(item => !readNotificationIds.value.includes(item.id)));
const visibleNotifications = computed(() => noticeExpanded.value ? unreadNotifications.value : unreadNotifications.value.slice(0, collapsedNoticeCount));

const toDate = (value?: string) => {
  if (!value) return null;
  const date = new Date(value.replace(' ', 'T'));
  return Number.isNaN(date.getTime()) ? null : date;
};

const formatDeadline = (value?: string) => {
  const date = toDate(value);
  if (!date) return '未设置';
  return `${date.getMonth() + 1}月${date.getDate()}日 ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

const formatRelativeTime = (value?: string) => {
  const date = toDate(value);
  if (!date) return '';
  const diff = Date.now() - date.getTime();
  const minutes = Math.max(1, Math.floor(diff / 60000));
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  return `${Math.floor(hours / 24)}天前`;
};

const fetchTodos = async () => {
  const events = await getTimePlans() as any[];
  todos.value = events
    .filter(event => ['作业', '考试', '个人'].includes(event.type))
    .sort((a, b) => (toDate(a.startTime)?.getTime() || 0) - (toDate(b.startTime)?.getTime() || 0))
    .slice(0, 5)
    .map(event => ({
      id: event.id,
      title: event.title,
      deadline: formatDeadline(event.endTime || event.startTime),
      highPriority: event.type === '考试' || event.type === '作业',
      completed: event.status === '已完成' || event.status === '已结束',
      raw: event
    }));
};

const fetchNotifications = async () => {
  notifications.value = await getDashboardNotifications();
};

const fetchAcademicOverview = async () => {
  const studentId = userStore.userInfo?.studentId;
  if (!studentId) return;
  try {
    const data: any = await getAcademicInfo(studentId);
    const earned = Number(data.graduationReq?.earned || 0);
    const total = Number(data.graduationReq?.total || 0);
    academicOverview.value = {
      earned: Number(earned.toFixed(1)),
      total: Number(total.toFixed(1)),
      percent: total > 0 ? Number(Math.min((earned / total) * 100, 100).toFixed(1)) : 0
    };
  } catch (error: any) {
    ElMessage.warning(error.message || '毕业进度加载失败');
  }
};

const loadReadNotifications = () => {
  try {
    readNotificationIds.value = JSON.parse(localStorage.getItem(readStorageKey.value) || '[]');
  } catch {
    readNotificationIds.value = [];
  }
};

const persistReadNotifications = () => {
  localStorage.setItem(readStorageKey.value, JSON.stringify(readNotificationIds.value));
};

const markNotificationRead = (id: string) => {
  if (!readNotificationIds.value.includes(id)) {
    readNotificationIds.value.push(id);
    persistReadNotifications();
  }
};

const toggleTodo = async (todo: TodoItem) => {
  const nextCompleted = !todo.completed;
  todo.completed = nextCompleted;
  try {
    await updateTimePlan(todo.id, { status: nextCompleted ? '已完成' : '待开始' });
    todo.raw.status = nextCompleted ? '已完成' : '待开始';
  } catch (error: any) {
    todo.completed = !nextCompleted;
    ElMessage.error(error.message || '待办状态更新失败');
  }
};

const getNotificationClass = (type: string) => {
  if (type === 'forum_comment') return 'bg-blue-50 text-blue-500 group-hover:bg-blue-500 group-hover:text-white';
  if (type === 'forum_like') return 'bg-orange-50 text-orange-500 group-hover:bg-orange-500 group-hover:text-white';
  return 'bg-green-50 text-green-500 group-hover:bg-green-500 group-hover:text-white';
};

const openNotification = (notice: DashboardNotification) => {
  markNotificationRead(notice.id);
  if (notice.targetUrl) {
    router.push(notice.targetUrl);
  }
};

const markAllRead = () => {
  readNotificationIds.value = Array.from(new Set([...readNotificationIds.value, ...notifications.value.map(item => item.id)]));
  noticeExpanded.value = false;
  persistReadNotifications();
};

onMounted(() => {
  loadReadNotifications();
  fetchAcademicOverview();
  fetchTodos();
  fetchNotifications();
});
</script>
