export type FeedbackRating = 'helpful' | 'not_helpful';

export interface AnswerFeedback {
  rating: FeedbackRating;
  reason_code?: string | null;
  comment?: string;
  updated_at?: string;
}

export interface QualityMetrics {
  rag_answers: number;
  answerable_count: number;
  answerable_rate: number;
  partial_count: number;
  no_knowledge_count: number;
  degraded_count: number;
  web_attempt_count: number;
  web_success_count: number;
  feedback_count: number;
  helpful_count: number;
  not_helpful_count: number;
  helpful_rate: number | null;
}

export interface QualityRun {
  session_id: string;
  message_index: number;
  username: string;
  timestamp: string;
  query: string;
  answer_excerpt: string;
  retrieval_status: string;
  retrieval_outcome: string;
  route: string;
  evidence_confidence?: number | null;
  retrieved_count: number;
  rerank_backend: string;
  rerank_applied: boolean;
  official_web_status: string;
  degraded_code: string;
  rating?: FeedbackRating | null;
  reason_code: string;
  comment: string;
}

export interface QualitySummary {
  period_days: number;
  generated_at: string;
  metrics: QualityMetrics;
  status_distribution: Record<string, number>;
  recent_runs: QualityRun[];
  failure_queue: QualityRun[];
}
