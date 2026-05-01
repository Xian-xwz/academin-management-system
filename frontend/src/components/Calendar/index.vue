<template>
  <el-calendar v-model="value" class="rounded-2xl border border-slate-100 shadow-sm time-calendar">
    <template #date-cell="{ data }">
      <div 
        class="h-full w-full p-2 relative flex flex-col group cursor-pointer hover:bg-slate-50/80 transition-colors"
        @click="$emit('day-click', data.date)"
      >
        <div class="mb-1 flex items-center justify-between">
          <span class="text-sm font-semibold" :class="{ 'text-blue-600': data.isSelected }">
          {{ data.day.split('-').slice(2).join('') }}
          </span>
          <span v-if="getEvents(data.date).length" class="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-500">
            {{ getEvents(data.date).length }}
          </span>
        </div>
        <div class="flex-1 overflow-hidden space-y-1.5">
          <div 
            v-for="event in getEvents(data.date)" 
            :key="event.id"
            class="rounded-lg border px-2 py-1 text-[10px] leading-tight shadow-sm transition-transform group-hover:translate-x-0.5"
            :class="getCardClass(event.type)"
            :title="event.title"
          >
            <div class="flex items-center gap-1">
              <span class="h-1.5 w-1.5 shrink-0 rounded-full" :class="getDotClass(event.type)"></span>
              <span class="truncate font-semibold">{{ event.title }}</span>
            </div>
            <div class="mt-0.5 truncate opacity-75">{{ formatTime(event.startTime) }}<span v-if="event.location"> · {{ event.location }}</span></div>
          </div>
        </div>
      </div>
    </template>
  </el-calendar>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';

const props = defineProps<{
  events: any[]
}>();

defineEmits(['day-click']);

const value = ref(new Date());

const toDate = (value: string | Date) => {
  if (value instanceof Date) return value;
  return new Date(value.replace(' ', 'T'));
};

const toDateKey = (value: string | Date) => {
  const date = toDate(value);
  if (Number.isNaN(date.getTime())) return '';
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

const getEvents = (date: Date) => {
  const dateString = toDateKey(date);
  return props.events.filter(e => e.startTime && toDateKey(e.startTime) === dateString);
};

const getDotClass = (type: string) => {
  const map: Record<string, string> = {
    '课程': 'bg-blue-500',
    '考试': 'bg-red-500',
    '作业': 'bg-orange-500',
    '个人': 'bg-green-500'
  };
  return map[type] || 'bg-gray-500';
}

const getCardClass = (type: string) => {
  const map: Record<string, string> = {
    '课程': 'border-blue-100 bg-blue-50 text-blue-700',
    '考试': 'border-rose-100 bg-rose-50 text-rose-700',
    '作业': 'border-amber-100 bg-amber-50 text-amber-700',
    '个人': 'border-emerald-100 bg-emerald-50 text-emerald-700'
  };
  return map[type] || 'border-slate-100 bg-slate-50 text-slate-700';
};

const formatTime = (dateValue: string | Date) => {
  const date = toDate(dateValue);
  if (Number.isNaN(date.getTime())) return '';
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
};

watch(
  () => props.events,
  (items) => {
    const firstEvent = [...items]
      .filter(item => item.startTime)
      .sort((a, b) => toDate(a.startTime).getTime() - toDate(b.startTime).getTime())[0];
    if (firstEvent?.startTime) {
      value.value = toDate(firstEvent.startTime);
    }
  },
  { immediate: true, deep: true }
);
</script>

<style scoped>
:deep(.el-calendar-table .el-calendar-day) {
  padding: 0;
  height: 128px;
}

:deep(.time-calendar .el-calendar__body) {
  padding: 12px 16px 18px;
}

:deep(.time-calendar .el-calendar-table td.is-selected) {
  background-color: #eff6ff;
}
</style>
