import { useState, useRef, useEffect } from 'react';
import { Upload, FileText, X, CheckCircle2 } from 'lucide-react';
import axios from 'axios';
import api from '@/lib/api';
import type { UploadResponse } from '@/types';
import { cn } from '@/lib/utils';
import { ErrorState } from '@/components/States';

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
    } catch (err: unknown) {
      if (axios.isCancel(err)) return;
      const apiError = axios.isAxiosError(err) ? err.response?.data?.error : undefined;
      setError(apiError || "Failed to upload file. Please make sure the backend API is running.");
    } finally { setIsUploading(false); }
  };

  const clearFile = () => {
    setFile(null); setError(null); setMappingInfo(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  return (
    <div className="w-full space-y-4">
      <div className="panel p-6 sm:p-7">
        <div className="mb-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="live-dot" aria-hidden="true" />
            <h2 className="text-sm font-semibold text-txt">Statement intake</h2>
            <span className="font-mono text-micro uppercase tracking-wider text-brand">Ready</span>
          </div>
          <span className="rounded border border-line px-1.5 py-0.5 font-mono text-micro text-txt-muted">CSV</span>
        </div>

        <div
          className={cn(
            'rounded-md border-2 border-dashed p-6 transition-[border-color,background-color,box-shadow] duration-200 ease-out',
            isDragging
              ? 'border-brand bg-brand/[0.06] ring-2 ring-brand/40'
              : 'border-brand/30 bg-brand/[0.03] hover:border-brand/50'
          )}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".csv" className="hidden" />
          {!file ? (
            <div className="flex flex-col items-start gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-md border border-line bg-tint-1">
                <Upload className="h-5 w-5 text-txt-muted" aria-hidden="true" />
              </div>
              <div>
                <p className="text-base font-medium text-txt">Drop your bank statement</p>
                <p className="mt-1 text-sm text-txt-muted">or browse for a .csv export</p>
              </div>
              <button onClick={() => fileInputRef.current?.click()} className="btn-ghost">
                Select file
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-start gap-5">
              <div className="flex w-full items-center gap-3 rounded-md border border-line bg-tint-2 p-3 text-left">
                <FileText className="h-5 w-5 flex-shrink-0 text-brand" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-txt">{file.name}</p>
                  <p className="font-mono text-micro text-txt-faint">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
                <button
                  onClick={clearFile}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded text-txt-muted transition-colors hover:bg-tint-3 hover:text-txt cursor-pointer"
                  disabled={isUploading}
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <button onClick={handleUpload} disabled={isUploading} className="btn-primary w-full sm:w-auto">
                {isUploading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Analyzing…
                  </>
                ) : (
                  'Analyze statement'
                )}
              </button>
            </div>
          )}
        </div>

        <p className="mt-4 flex items-center gap-2 text-caption text-txt-faint">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          Parsed on a local server and deleted when the session ends.
        </p>
      </div>

      {error && <ErrorState message={error} />}

      {mappingInfo && (
        <div className="rounded-md border border-success/25 bg-success/[0.06] p-4 text-sm">
          <div className="mb-3 flex items-center gap-2 font-medium text-success">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            <p>Columns mapped</p>
          </div>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
            <Mapped label="Date" value={mappingInfo.date_column} />
            <Mapped label="Description" value={mappingInfo.description_column} />
            <Mapped label="Amount" value={mappingInfo.amount_pattern} />
            {mappingInfo.rows_skipped > 0 && (
              <div className="flex items-baseline gap-2">
                <dt className="text-txt-faint">Skipped</dt>
                <dd className="font-mono text-warning">{mappingInfo.rows_skipped} rows</dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

function Mapped({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-2">
      <dt className="text-txt-faint">{label}</dt>
      <dd className="truncate font-mono text-txt">{value}</dd>
    </div>
  );
}
