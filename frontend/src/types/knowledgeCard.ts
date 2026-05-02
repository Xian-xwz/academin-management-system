export interface KnowledgeCardItem {
  id: number;
  title?: string;
  inputType: 'text' | 'image' | 'mixed';
  templateId?: string;
  imageNumber?: string;
  routeReason?: string;
  status: 'processing' | 'succeeded' | 'failed';
  outputImageUrl?: string;
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
}

export interface KnowledgeCardDetail extends KnowledgeCardItem {
  inputText?: string;
  inputImageUrl?: string;
  prompt?: string;
  extraPrompt?: string;
  difyWorkflowRunId?: string;
  difyTaskId?: string;
  rawResponse?: Record<string, any>;
}

export interface KnowledgeCardListResponse {
  items: KnowledgeCardItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface KnowledgeCardStreamHandlers {
  onStatus?: (message: string, cardId?: number) => void;
  onWorkflow?: (message: string, node?: string, cardId?: number) => void;
  onPreview?: (imageUrl: string, cardId?: number) => void;
  onDone?: (card: KnowledgeCardDetail) => void;
  onError?: (message: string, cardId?: number) => void;
}
