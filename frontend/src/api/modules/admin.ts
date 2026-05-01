import request from '@/api';

const unwrapResponse = <T>(res: any): T => {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) {
    return res.data as T;
  }
  return res as T;
};

export interface AdminMajorStat {
  majorCode?: string | null;
  majorName?: string | null;
  count: number;
}

export interface AdminDashboardSummary {
  totalUsers: number;
  activeUsers: number;
  studentUsers: number;
  adminUsers: number;
  majorDistribution: AdminMajorStat[];
}

export interface AdminUserItem {
  id: number;
  username: string;
  studentId: string;
  name: string;
  avatarUrl?: string | null;
  majorCode?: string | null;
  majorName?: string | null;
  grade?: string | null;
  role: string;
  isActive: boolean;
  createdAt: string;
}

export interface AdminUserDetail extends AdminUserItem {
  email?: string | null;
  updatedAt: string;
}

export interface AdminUserListResponse {
  items: AdminUserItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface AdminForumTopicItem {
  id: number;
  title: string;
  author: string;
  authorStudentId: string;
  majorName?: string | null;
  status: string;
  views: number;
  likes: number;
  comments: number;
  createdAt: string;
}

export interface AdminForumTopicListResponse {
  items: AdminForumTopicItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface AdminUserQuery {
  page?: number;
  pageSize?: number;
  q?: string;
  majorCode?: string;
  role?: string;
  isActive?: boolean;
}

export const getAdminDashboardSummary = async () => {
  const res = await request.get('/admin/dashboard/summary');
  return unwrapResponse<AdminDashboardSummary>(res);
};

export const getAdminUsers = async (params?: AdminUserQuery) => {
  const res = await request.get('/admin/users', { params });
  return unwrapResponse<AdminUserListResponse>(res);
};

export const getAdminUserDetail = async (studentId: string) => {
  const res = await request.get(`/admin/users/${studentId}`);
  return unwrapResponse<AdminUserDetail>(res);
};

export const getAdminUserAcademicInfo = async (studentId: string) => {
  const res = await request.get(`/admin/users/${studentId}/academic-info`);
  return unwrapResponse(res);
};

export const getAdminUserGraduationProgress = async (studentId: string) => {
  const res = await request.get(`/admin/users/${studentId}/graduation-progress`);
  return unwrapResponse(res);
};

export const sendAdminAcademicWarning = async (studentId: string, data: { title: string; content: string }) => {
  const res = await request.post(`/admin/users/${studentId}/warnings`, data);
  return unwrapResponse(res);
};

export const getAdminForumTopics = async (params?: { page?: number; pageSize?: number; q?: string; status?: string }) => {
  const res = await request.get('/admin/forum/topics', { params });
  return unwrapResponse<AdminForumTopicListResponse>(res);
};

export const hideAdminForumTopic = async (topicId: number | string) => {
  const res = await request.delete(`/admin/forum/topics/${topicId}`);
  return unwrapResponse(res);
};

/** 管理员设置帖子状态：normal 恢复显示，deleted 隐藏（软删除） */
export const patchAdminForumTopicStatus = async (topicId: number | string, data: { status: 'normal' | 'deleted' }) => {
  const res = await request.patch(`/admin/forum/topics/${topicId}`, data);
  return unwrapResponse(res);
};
