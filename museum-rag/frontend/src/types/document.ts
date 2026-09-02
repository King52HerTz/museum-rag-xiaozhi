export interface DocumentItem {
  filename: string;
  file_type: string;
  chunk_count: number;
  museum?: string | null;
  exhibition?: string | null;
  exhibit_id?: string | null;
  era?: string | null;
  category?: string | null;
}

export interface DocumentProfilePayload {
  museum: string;
  exhibition: string;
  exhibit_id: string;
  era: string;
  category: string;
}

export type DocumentProfilePatch = Partial<DocumentProfilePayload>;
export type DocumentProfileKey = keyof DocumentProfilePayload;

export interface DocumentFilters {
  keyword: string;
  museum: string;
  exhibition: string;
  era: string;
  category: string;
}

export type DocumentFilterKey = keyof DocumentFilters;
export type DocumentBatchApplyState = Record<DocumentProfileKey, boolean>;

export interface UploadStep {
  key: string;
  label: string;
  percent: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message: string;
}

export interface UploadJob {
  job_id: string;
  status: 'running' | 'completed' | 'failed';
  message: string;
  steps: UploadStep[];
}

export interface DeleteStep {
  key: string;
  label: string;
  percent: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  message: string;
}

export interface DeleteJob {
  job_id: string;
  status: 'running' | 'completed' | 'failed';
  message: string;
  steps: DeleteStep[];
}

export interface ActiveDeleteJob {
  jobId?: string;
  status: 'running' | 'completed' | 'failed';
  message: string;
  collapsed: boolean;
  steps: DeleteStep[];
}
