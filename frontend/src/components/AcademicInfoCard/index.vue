<template>
  <div class="space-y-6">
    <el-card shadow="hover">
      <template #header>
        <div class="font-bold text-lg">学生基本信息</div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="姓名">{{ data.baseInfo.name }}</el-descriptions-item>
        <el-descriptions-item label="学号">{{ data.baseInfo.studentId }}</el-descriptions-item>
        <el-descriptions-item label="专业">{{ data.baseInfo.major }}</el-descriptions-item>
        <el-descriptions-item label="年级">{{ data.baseInfo.grade }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="font-bold text-lg flex items-center justify-between">
          <span>毕业要求进度</span>
          <span class="text-sm font-normal text-gray-500">已修 {{ data.graduationReq.earned }} / 要求 {{ data.graduationReq.total }}</span>
        </div>
      </template>
      <el-progress 
        :percentage="Math.round((data.graduationReq.earned / data.graduationReq.total) * 100)" 
        :stroke-width="20" 
        text-inside 
      />
      
      <div class="mt-6">
        <h4 class="font-semibold mb-4 text-gray-700">课程分类统计</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div v-for="stat in data.statistics" :key="stat.category" class="bg-gray-50 p-3 rounded">
            <div class="flex justify-between text-sm mb-1">
              <span class="font-medium">{{ stat.category }}</span>
              <span>{{ stat.earned }} / {{ stat.total }} 学分</span>
            </div>
            <el-progress 
              :percentage="stat.total === 0 ? 0 : Math.round((stat.earned / stat.total) * 100)" 
              :status="stat.earned >= stat.total ? 'success' : ''" 
              :show-text="false"
            />
          </div>
        </div>
      </div>
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="font-bold text-lg">已修课程清单</div>
      </template>
      <el-table :data="data.courses" stripe style="width: 100%">
        <el-table-column prop="term" label="修读学期" width="120" />
        <el-table-column prop="name" label="课程名称" />
        <el-table-column prop="category" label="课程类别" width="120" />
        <el-table-column prop="credit" label="学分" width="80" align="center" />
        <el-table-column prop="score" label="成绩" width="80" align="center" />
      </el-table>
    </el-card>

    <el-card shadow="hover" class="border-orange-200">
      <template #header>
        <div class="font-bold text-lg text-orange-600">还需修读建议</div>
      </template>
      <el-alert
        v-for="sug in data.suggestions"
        :key="sug.category"
        :title="`${sug.category}（缺 ${sug.gap} 学分）`"
        :description="sug.desc"
        type="warning"
        show-icon
        :closable="false"
        class="mb-3"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  data: any
}>();
</script>
