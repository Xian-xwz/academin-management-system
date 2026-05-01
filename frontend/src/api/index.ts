import axios from 'axios';
import { getToken, removeToken } from '@/utils/auth';
import router from '@/router';
import { ElMessage } from 'element-plus';

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 60000,
});

// Request Interceptor
request.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor
request.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      removeToken();
      ElMessage.error('登录状态已过期，请重新登录');
      router.push('/login');
    } else {
      ElMessage.error(error.message || '网络或服务器错误');
    }
    return Promise.reject(error);
  }
);

export default request;
