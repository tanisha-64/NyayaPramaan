import { apiUpload, apiGet, apiDelete } from "./apiClient";

export type UploadResponse = {
  case_id: string;
  file_url: string;
  filename: string;
  status: string;
  document_type: string;
};

export type CaseStatus = {
  status: string;
  summary: string;
  timeline: string;
};

/**
 * All accepted file formats for document upload.
 * PDF, DOCX, DOC, TXT for text extraction.
 * JPG, JPEG, PNG, TIFF, BMP, WEBP for OCR (Tesseract on backend).
 */
export const ACCEPTED_FORMATS =
  ".pdf,.docx,.doc,.txt,.jpg,.jpeg,.png,.tiff,.bmp,.webp";

export const ACCEPTED_MIME_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/msword",
  "text/plain",
  "image/jpeg",
  "image/png",
  "image/tiff",
  "image/bmp",
  "image/webp",
];

/**
 * Validate file type before uploading.
 * Returns an error string if invalid, or null if valid.
 */
export function validateFileType(file: File): string | null {
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  const validExts = ["pdf", "docx", "doc", "txt", "jpg", "jpeg", "png", "tiff", "bmp", "webp"];
  if (!validExts.includes(ext)) {
    return `Unsupported file format ".${ext}". Accepted formats: PDF, DOCX, DOC, TXT, JPG, PNG, TIFF, BMP, WEBP`;
  }
  // 50MB limit
  if (file.size > 50 * 1024 * 1024) {
    return `File too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum size is 50MB.`;
  }
  return null;
}

export function uploadDocument(file: File, signal?: AbortSignal) {
  return apiUpload<UploadResponse>("/document/upload", file, signal);
}

export function getCaseStatus(caseId: string) {
  return apiGet<CaseStatus>(`/document/${caseId}/status`);
}

export function deleteDocument(caseId: string) {
  return apiDelete(`/document/${caseId}`);
}