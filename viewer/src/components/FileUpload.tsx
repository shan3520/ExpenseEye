import { useState, useRef, useEffect } from 'react';
import { Upload, FileText, X, AlertCircle, CheckCircle2 } from 'lucide-react';
import api from '@/lib/api';
import type { UploadResponse } from '@/types';
import { cn } from '@/lib/utils';

interface FileUploadProps {
  onUploadSuccess: (sessionId: string) => void;
}

export function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mappingInfo, setMappingInfo] = useState<UploadResponse['mapping_info'] | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = (e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); };
  const isCsvFile = (f: File) => f.type === 'text/csv' || f.name.endsWith('.csv');

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0];
      if (isCsvFile(droppedFile)) { setFile(droppedFile); setError(null); setMappingInfo(null); }
      else { setError("Please upload a valid CSV file."); }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      if (isCsvFile(selectedFile)) { setFile(selectedFile); setError(null); setMappingInfo(null); }
      else { setError("Please upload a valid CSV file."); }
    }
  };

  const uploadAbortRef = useRef<AbortController | null>(null);
  useEffect(() => { return () => { uploadAbortRef.current?.abort(); }; }, []);

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true); setError(null);
    const formData = new FormData();
    formData.append('file', file);
    const controller = new AbortController();
    uploadAbortRef.current = controller;
    try {
      const response = await api.post<UploadResponse>('/upload', formData, { signal: controller.signal });
      if (response.data.success) { setMappingInfo(response.data.mapping_info); onUploadSuccess(response.data.session_id); }
    } catch (err: any) {
      if (err.name === 'AbortError' || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') return;
      setError(err.response?.data?.error || "Failed to upload file. Please make sure the backend API is running.");
    } finally { setIsUploading(false); }
  };

  const clearFile = () => {
    setFile(null); setError(null); setMappingInfo(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="w-full max-w-3xl mx-auto space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
        <div className="text-sm text-blue-800">
          <p className="font-semibold mb-1">Privacy-first</p>
          <p>Your file is processed temporarily on the local server and deleted automatically after the session.</p>
        </div>
      </div>
      <div
        className={cn("border-2 border-dashed rounded-xl p-8 text-center transition-colors",
          isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400")}
        onDragOver={handleDragOver} onDragLeave={handleDragLeave} onDrop={handleDrop}
      >
        <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".csv" className="hidden" />
        {!file ? (
          <div className="flex flex-col items-center gap-4">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
              <Upload className="w-8 h-8 text-gray-500" />
            </div>
            <div>
              <p className="text-lg font-medium text-gray-900">Upload your bank statement</p>
              <p className="text-sm text-gray-500 mt-1">Drag and drop your CSV file here, or click to browse</p>
            </div>
            <button onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 bg-white border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50">
              Select File
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-4">
            <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg border border-gray-200 w-full max-w-md">
              <FileText className="w-8 h-8 text-blue-500 flex-shrink-0" />
              <div className="flex-1 min-w-0 text-left">
                <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(2)} KB</p>
              </div>
              <button onClick={clearFile} className="p-1 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-200" disabled={isUploading}>
                <X className="w-5 h-5" />
              </button>
            </div>
            <button onClick={handleUpload} disabled={isUploading}
              className="px-6 py-2.5 bg-blue-600 text-white rounded-md shadow-sm text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
              {isUploading ? (
                <><svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>Analyzing...</>
              ) : 'Analyze Statement'}
            </button>
          </div>
        )}
      </div>
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3 text-sm text-red-800">
          <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" /><p>{error}</p>
        </div>
      )}
      {mappingInfo && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm">
          <div className="flex items-center gap-2 text-green-800 font-medium mb-3">
            <CheckCircle2 className="w-5 h-5" /><p>Upload Successful</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-green-900 bg-white/60 rounded-md p-3">
            <div>
              <p><span className="font-semibold">Date Column:</span> {mappingInfo.date_column}</p>
              <p><span className="font-semibold">Description Column:</span> {mappingInfo.description_column}</p>
            </div>
            <div>
              <p><span className="font-semibold">Amount Pattern:</span> {mappingInfo.amount_pattern}</p>
              {mappingInfo.rows_skipped > 0 && <p className="text-yellow-600">⚠️ Skipped {mappingInfo.rows_skipped} invalid rows</p>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
