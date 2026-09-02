from typing import List, Optional

from pydantic import BaseModel


class DocumentInfo(BaseModel):
    filename: str
    file_type: str
    chunk_count: int
    uploaded_at: Optional[str] = None
    museum: Optional[str] = None
    exhibition: Optional[str] = None
    exhibit_id: Optional[str] = None
    era: Optional[str] = None
    category: Optional[str] = None


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]


class DocumentUploadResponse(BaseModel):
    filename: str
    chunks_processed: int
    message: str
    museum: Optional[str] = None
    exhibition: Optional[str] = None
    exhibit_id: Optional[str] = None
    era: Optional[str] = None
    category: Optional[str] = None


class DocumentUploadStartResponse(BaseModel):
    job_id: str
    filename: str
    message: str
    museum: Optional[str] = None
    exhibition: Optional[str] = None
    exhibit_id: Optional[str] = None
    era: Optional[str] = None
    category: Optional[str] = None


class DocumentProfileUpdateRequest(BaseModel):
    museum: Optional[str] = None
    exhibition: Optional[str] = None
    exhibit_id: Optional[str] = None
    era: Optional[str] = None
    category: Optional[str] = None


class DocumentProfileBatchUpdateRequest(DocumentProfileUpdateRequest):
    filenames: List[str]


class UploadStepInfo(BaseModel):
    key: str
    label: str
    percent: int
    status: str
    message: str = ""


class DocumentUploadJobResponse(BaseModel):
    job_id: str
    filename: str
    status: str
    current_step: str
    message: str
    total_chunks: int = 0
    processed_chunks: int = 0
    error: Optional[str] = None
    created_at: str
    updated_at: str
    steps: List[UploadStepInfo]


class DocumentDeleteStartResponse(BaseModel):
    job_id: str
    filename: str
    message: str


class DocumentDeleteJobResponse(DocumentUploadJobResponse):
    pass


class DocumentDeleteResponse(BaseModel):
    filename: str
    chunks_deleted: int
    message: str
