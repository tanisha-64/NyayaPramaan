
import { apiUpload, apiDelete } from "./apiClient";



export type UploadResponse = {

  case_id: string; file_url: string; filename: string;

  summary: string; timeline: string; document_type: string;

};



export function uploadDocument(file: File) {

  return apiUpload<UploadResponse>("/document/upload", file);

}



export function deleteDocument(caseId: string) {

  return apiDelete(`/document/${caseId}`);

}

