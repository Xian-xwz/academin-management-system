<template>
  <el-config-provider namespace="el">
    <router-view />
  </el-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { ElConfigProvider } from 'element-plus';

onMounted(() => {
  const savedColor = localStorage.getItem('theme-color');
  
  if (savedColor) {
    // Only basic setting for App init, Profile page handles full update
    document.documentElement.style.setProperty('--el-color-primary', savedColor);
  }
});
</script>

<style>
/* 全局基础重置样式 */
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  background-color: #f3f4f6;
}
#app {
  height: 100%;
}
</style>
