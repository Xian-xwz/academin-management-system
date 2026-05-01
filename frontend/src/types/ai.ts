export interface KnowledgeSource {
  title: string;
  datasetName?: string;
  documentName?: string;
  score?: number;
  content?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
  loading?: boolean;
  sources?: KnowledgeSource[];
  intent?: string;
  statusSteps?: string[];
  currentStatus?: string;
}

export interface ChatSession {
  id: string;
  title?: string;
  time?: string;
}

export interface SendChatRequest {
  query: string;
  conversation_id?: string;
  student_id?: string;
  major_code?: string;
  major_name?: string;
  intent?: 'general_qa' | 'graduation_requirements' | 'graduation_audit' | 'course_advice';
  inputs?: Record<string, any>;
  files?: DifyChatFile[];
}

export interface DifyChatFile {
  type: string;
  transfer_method: 'local_file';
  upload_file_id: string;
}

export interface DifyUploadedFile {
  id: string;
  name?: string;
  size?: number;
  extension?: string;
  mime_type?: string;
  type: string;
}

export interface SendChatResponse {
  answer: string;
  conversation_id: string;
  sources?: KnowledgeSource[];
  intent?: string;
  need_personal_data?: boolean;
}

export interface ChatHistoryResponse {
  conversation_id: string;
  title?: string;
  messages: Array<{
    role: 'user' | 'assistant';
    content: string;
    intent?: string;
    sources?: KnowledgeSource[];
    need_personal_data?: boolean;
  }>;
}
