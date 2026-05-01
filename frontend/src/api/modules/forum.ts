import request from '@/api';
import { getToken } from '@/utils/auth';

const unwrapResponse = <T>(res: any): T => {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) {
    return res.data as T;
  }
  return res as T;
};

const formatSize = (size?: number | null) => {
  if (!size) return '0B';
  if (size > 1024 * 1024) return `${(size / 1024 / 1024).toFixed(1)}MB`;
  if (size > 1024) return `${(size / 1024).toFixed(1)}KB`;
  return `${size}B`;
};

const normalizeFile = (file: any) => ({
    ...file,
    name: file.originalName,
    size: formatSize(file.fileSize),
    url: getFileDownloadUrl(file.id)
});

const normalizeComment = (comment: any): any => ({
  ...comment,
  attachments: (comment.attachments || []).map(normalizeFile),
  replies: (comment.replies || []).map(normalizeComment)
});

const normalizeTopic = (topic: any) => ({
  ...topic,
  attachments: (topic.attachments || []).map(normalizeFile),
  comments: (topic.comments || []).map(normalizeComment)
});

export const getTopics = async (params?: any) => {
  const res = await request.get('/forum/topics', { params });
  return (unwrapResponse<any[]>(res) || []).map(normalizeTopic);
};

export const getForumMajors = async () => {
  const res = await request.get('/forum/majors');
  return unwrapResponse<Array<{ code: string; name: string }>>(res) || [];
};

export const getTopicDetail = async (id: string | number) => {
  const res = await request.get(`/forum/topics/${id}`);
  return normalizeTopic(unwrapResponse(res));
};

export const createTopic = async (data: any) => {
  const res = await request.post('/forum/topics', data);
  return normalizeTopic(unwrapResponse(res));
};

export const updateTopic = async (id: string | number, data: any) => {
  const res = await request.put(`/forum/topics/${id}`, data);
  return normalizeTopic(unwrapResponse(res));
};

export const deleteTopic = async (id: string | number) => {
  const res = await request.delete(`/forum/topics/${id}`);
  return unwrapResponse(res);
};

export const uploadTopicFile = async (topicId: string | number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await request.post(`/forum/topics/${topicId}/files`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return normalizeFile(unwrapResponse(res));
};

export const addComment = async (topicId: string | number, data: any) => {
  const res = await request.post(`/forum/topics/${topicId}/comments`, data);
  return normalizeComment(unwrapResponse(res));
};

export const uploadCommentFile = async (topicId: string | number, commentId: string | number, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await request.post(`/forum/topics/${topicId}/comments/${commentId}/files`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return normalizeFile(unwrapResponse(res));
};

export const likeTopic = async (topicId: string | number) => {
  const res = await request.post(`/forum/topics/${topicId}/like`);
  return unwrapResponse(res);
};

export const unlikeTopic = async (topicId: string | number) => {
  const res = await request.delete(`/forum/topics/${topicId}/like`);
  return unwrapResponse(res);
};

export const getFileDownloadUrl = (fileId: string | number) => `/api/forum/files/${fileId}/download`;

export const downloadForumFile = async (file: any) => {
  const token = getToken();
  const apiBase = import.meta.env.VITE_API_BASE || '/api';
  const response = await fetch(`${apiBase}/forum/files/${file.id}/download`, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });

  if (!response.ok) {
    throw new Error(`附件下载失败：${response.status}`);
  }

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = file.name || file.originalName || 'attachment';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
};
