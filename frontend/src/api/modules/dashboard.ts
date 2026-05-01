import request from '@/api';

const unwrapResponse = <T>(res: any): T => {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) {
    return res.data as T;
  }
  return res as T;
};

export interface DashboardNotification {
  id: string;
  type: 'forum_comment' | 'forum_like' | 'ai_chat' | string;
  title: string;
  content: string;
  time?: string;
  targetUrl?: string;
  read?: boolean;
}

export const getDashboardNotifications = async () => {
  const res = await request.get('/dashboard/notifications');
  return unwrapResponse<DashboardNotification[]>(res) || [];
};
