import request from '@/api';
import { getToken } from '@/utils/auth';
import { ChatHistoryResponse, ChatSession, DifyUploadedFile, SendChatRequest, SendChatResponse } from '@/types/ai';

export const inferIntent = (query: string): 'general_qa' | 'graduation_requirements' | 'graduation_audit' | 'course_advice' => {
  if (query.includes('毕业条件') || query.includes('毕业要求') || query.includes('要修多少分')) {
    return 'graduation_requirements';
  }
  if (query.includes('我能不能毕业') || query.includes('还差多少') || query.includes('学分够不够')) {
    return 'graduation_audit';
  }
  if (query.includes('选课') || query.includes('下学期修什么') || query.includes('课程建议')) {
    return 'course_advice';
  }
  return 'general_qa';
};

const unwrapResponse = <T>(res: any): T => {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) {
    return res.data as T;
  }
  return res as T;
};

export const sendMessage = async (data: SendChatRequest): Promise<SendChatResponse> => {
  const payload = {
    ...data,
    intent: data.intent || inferIntent(data.query)
  };
  const res = await request.post('/ai/chat', payload);
  return unwrapResponse<SendChatResponse>(res);
};

export const sendMessageStream = async (
  data: SendChatRequest,
  handlers: {
    onMessage?: (chunk: string) => void;
    onReplace?: (answer: string) => void;
    onStatus?: (message: string) => void;
    onEnd?: (payload: Partial<SendChatResponse>) => void;
    onError?: (message: string) => void;
  }
): Promise<void> => {
  const payload = {
    ...data,
    intent: data.intent || inferIntent(data.query)
  };
  const token = getToken();
  const apiBase = import.meta.env.VITE_API_BASE || '/api';
  const response = await fetch(`${apiBase}/ai/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok || !response.body) {
    throw new Error(`AI 服务请求失败：${response.status}`);
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
      if (event.event === 'message') {
        handlers.onMessage?.(event.answer || '');
      } else if (event.event === 'message_replace') {
        handlers.onReplace?.(event.answer || '');
      } else if (event.event === 'status') {
        handlers.onStatus?.(event.message || '');
      } else if (event.event === 'message_end') {
        handlers.onEnd?.({
          conversation_id: event.conversation_id,
          sources: event.sources || [],
          intent: event.intent,
          answer: ''
        });
      } else if (event.event === 'error') {
        handlers.onError?.(event.message || 'AI 流式响应异常');
      }
    }
  }
};

export const sendChatMessage = async (message: string) => {
  return sendMessage({ query: message }); // 保持向后兼容
};

export const getChatConversations = async (): Promise<ChatSession[]> => {
  const res = await request.get('/ai/conversations');
  return unwrapResponse<ChatSession[]>(res) || [];
};

export const getChatHistory = async (conversationId: string): Promise<ChatHistoryResponse> => {
  const res = await request.get(`/ai/conversations/${conversationId}`);
  return unwrapResponse<ChatHistoryResponse>(res);
};

export const deleteChatConversation = async (conversationId: string): Promise<void> => {
  await request.delete(`/ai/conversations/${conversationId}`);
};

export const uploadAiFile = async (file: File): Promise<DifyUploadedFile> => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await request.post('/ai/files/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return unwrapResponse<DifyUploadedFile>(res);
};
