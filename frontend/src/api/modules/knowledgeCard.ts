import request from '@/api';
import { getToken } from '@/utils/auth';
import { KnowledgeCardDetail, KnowledgeCardListResponse, KnowledgeCardStreamHandlers } from '@/types/knowledgeCard';

const unwrapResponse = <T>(res: any): T => {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) {
    return res.data as T;
  }
  return res as T;
};

export const getKnowledgeCards = async (params: {
  page?: number;
  pageSize?: number;
  status?: string;
  q?: string;
} = {}): Promise<KnowledgeCardListResponse> => {
  const res = await request.get('/knowledge-cards', { params });
  return unwrapResponse<KnowledgeCardListResponse>(res);
};

export const getKnowledgeCard = async (id: number): Promise<KnowledgeCardDetail> => {
  const res = await request.get(`/knowledge-cards/${id}`);
  return unwrapResponse<KnowledgeCardDetail>(res);
};

export const loadKnowledgeCardImage = async (url: string): Promise<string> => {
  const token = getToken();
  const apiBase = import.meta.env.VITE_API_BASE || '/api';
  const target = url.startsWith('/api') ? url : `${apiBase}${url.startsWith('/') ? url : `/${url}`}`;
  const response = await fetch(target, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });
  if (!response.ok) {
    throw new Error('图片加载失败');
  }
  const blob = await response.blob();
  return URL.createObjectURL(blob);
};

export const generateKnowledgeCardStream = async (
  form: {
    inputText?: string;
    extraPrompt?: string;
    image?: File | null;
  },
  handlers: KnowledgeCardStreamHandlers
): Promise<void> => {
  const body = new FormData();
  if (form.inputText?.trim()) body.append('inputText', form.inputText.trim());
  if (form.extraPrompt?.trim()) body.append('extraPrompt', form.extraPrompt.trim());
  if (form.image) body.append('image', form.image);

  const token = getToken();
  const apiBase = import.meta.env.VITE_API_BASE || '/api';
  const response = await fetch(`${apiBase}/knowledge-cards/stream`, {
    method: 'POST',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body
  });

  if (!response.ok || !response.body) {
    throw new Error(`知识卡片服务请求失败：${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';

    for (const rawEvent of events) {
      const dataLine = rawEvent.split('\n').find(line => line.startsWith('data:'));
      if (!dataLine) continue;
      const event = JSON.parse(dataLine.replace(/^data:\s*/, ''));
      if (event.event === 'status') {
        handlers.onStatus?.(event.message || '', event.cardId);
      } else if (event.event === 'workflow') {
        handlers.onWorkflow?.(event.message || '', event.node, event.cardId);
      } else if (event.event === 'preview') {
        handlers.onPreview?.(event.imageUrl || '', event.cardId);
      } else if (event.event === 'done') {
        handlers.onDone?.(event.card);
      } else if (event.event === 'error') {
        handlers.onError?.(event.message || '知识卡片生成失败', event.cardId);
      }
    }
  }
};
