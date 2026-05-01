<template>
  <div class="overflow-x-auto bg-white border border-gray-200 rounded-lg shadow-sm">
    <table class="w-full border-collapse min-w-[700px] text-sm text-center table-fixed">
      <thead class="bg-blue-50 text-gray-700 font-semibold border-b border-gray-200">
        <tr>
          <th class="border-r border-gray-200 p-3 w-20 bg-blue-100">节次</th>
          <th class="border-r border-gray-200 p-3 w-32" v-for="day in days" :key="day">{{ day }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(sectionName, rIndex) in sectionsList" :key="rIndex" class="border-b border-gray-200 hover:bg-gray-50">
          <td class="border-r border-gray-200 p-2 bg-gray-50 font-medium text-gray-600 w-20">
            {{ sectionName }}
          </td>
          <td 
            class="border-r border-gray-200 p-1 h-32 align-top relative cursor-pointer group hover:bg-blue-50 transition-colors w-32" 
            v-for="cIndex in 7" :key="cIndex"
            @click="handleCellClick(getCellCourse(cIndex, rIndex))"
          >
            <div v-if="getCellCourse(cIndex, rIndex)" class="h-full w-full bg-blue-100/70 border border-blue-200 text-blue-800 rounded p-2 shadow-sm text-xs flex flex-col items-center justify-center overflow-hidden hover:shadow-md transition-shadow relative">
              <div class="font-bold mb-1 truncate">{{ getCellCourse(cIndex, rIndex).name }}</div>
              <div class="truncate text-gray-600">{{ getCellCourse(cIndex, rIndex).location }}</div>
              <div class="text-gray-600 truncate">{{ getCellCourse(cIndex, rIndex).weeks }}</div>
              <div class="mt-1 flex items-center justify-center space-x-1 text-gray-700">
                 <el-icon><User /></el-icon>
                 <span class="truncate">{{ getCellCourse(cIndex, rIndex).teacher }}</span>
              </div>
              <div v-if="getCellCourse(cIndex, rIndex).note" class="absolute top-1 right-1 text-orange-500" title="有备注">
                <el-icon><Warning /></el-icon>
              </div>
            </div>
            <div v-else class="h-full w-full flex items-center justify-center text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
              <el-icon><Plus /></el-icon>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { User, Warning, Plus } from '@element-plus/icons-vue';

const props = defineProps<{
  courses: any[]
}>();

const emit = defineEmits(['edit-note']);

const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const sectionsList = [
  '1-2 节\n08:00-09:40', 
  '3-4 节\n10:00-11:40', 
  '5-6 节\n14:00-15:40', 
  '7-8 节\n16:00-17:40', 
  '9-10 节\n19:00-20:40'
];

const getCellCourse = (dayIndex: number, sectionGroupIndex: number) => {
  return props.courses.find(c => {
    // dayIndex 1-7, row index 0-4 targets section [1,2], [3,4]
    const targetSection = sectionGroupIndex * 2 + 1; 
    return c.day === dayIndex && c.sections.includes(targetSection);
  });
};

const handleCellClick = (course: any) => {
  if (course) {
    emit('edit-note', course);
  }
};
</script>

<style scoped>
td {
  word-break: break-all;
}
</style>
