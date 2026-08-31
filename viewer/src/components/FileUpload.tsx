import { useState, useRef, useEffect } from 'react';
// Phosphor Light to match the landing surface; weight is inherited from the
// IconContext provider in App's <Landing>, which wraps this component.
import { UploadSimple, FileText, X, CheckCircle } from '@phosphor-icons/react';
import axios from 'axios';
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
  const [slowWake, setSlowWake] = useState(false);
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
    setIsUploading(true); setError(null); setSlowWake(false);
    const formData = new FormData();
    formData.append('file', file);
    const controller = new AbortController();
    uploadAbortRef.current = controller;
    // After ~8s an idle Render instance is almost certainly cold-starting, so
    // switch the status text to an honest "waking" message rather than implying
    // the analysis itself is slow (P0-1).
    const wakeTimer = window.setTimeout(() => setSlowWake(true), 8000);
    try {
      const response = await api.post<UploadResponse>('/upload', formData, { signal: controller.signal });
      if (response.data.success) { setMappingInfo(response.data.mapping_info); onUploadSuccess(response.data.session_id); }
    } catch (err: unknown) {
      if (axios.isCancel(err)) return;
      const apiError = axios.isAxiosError(err) ? err.response?.data?.error : undefined;
      setError(apiError || "Couldn't reach the parser — it may still be waking up. Please try again in a moment.");
    } finally { window.clearTimeout(wakeTimer); setIsUploading(false); setSlowWake(false); }
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
            // border-style flips dashed → solid on hover/drag; border-color
            // animates over 0.3s for the soft solidify the brief calls for.
            'rounded-md border-2 p-6',
            isDragging
              ? 'is-dragging border-solid border-brand bg-brand/[0.06] ring-2 ring-brand/40'
              : 'border-dashed border-brand/30 bg-brand/[0.03] hover:border-solid hover:border-brand'
          )}
          // Transform handled inline so border/bg keep their ease-out while the
          // scale lifts on dragover (standard ease) and settles with a slight
          // spring overshoot on release. Reduced motion neutralizes both via the
          // global transition-duration override.
          style={{
            transform: isDragging ? 'scale(1.01)' : 'scale(1)',
            willChange: isDragging ? 'transform' : 'auto',
            transition: isDragging
              ? 'transform 200ms cubic-bezier(0.32,0.72,0,1), border-color 300ms ease-out, background-color 300ms ease-out, box-shadow 300ms ease-out'
              : 'transform 300ms cubic-bezier(0.34,1.56,0.64,1), border-color 300ms ease-out, background-color 300ms ease-out, box-shadow 300ms ease-out',
          }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <input type="file" ref={fileInputRef} onChange={handleFileChange} accept=".csv" className="hidden" />
          {!file ? (
            <div className="flex flex-col items-start gap-4">
              {/* Upload glyph over a breathing phosphor ring — an invitation to
                  drop. The ring stills while a file is dragged over (.is-dragging
                  on the parent zone) and under reduced motion. */}
              <div className="relative">
                <span
                  aria-hidden="true"
                  className="upload-pulse absolute inset-0 rounded-md bg-brand/15"
                />
                <div className="relative flex h-12 w-12 items-center justify-center rounded-md border border-line bg-tint-1">
                  <UploadSimple className="h-5 w-5 text-brand" aria-hidden="true" />
                </div>
              </div>
              <div>
                <p className="text-base font-medium text-txt">Drop your bank statement</p>
                <p className="mt-1 text-sm text-txt-muted">or browse for a .csv export</p>
              </div>
              <button
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex min-h-11 items-center justify-center rounded-full border border-line-strong bg-tint-2 px-5 py-2.5 text-sm font-medium text-txt-muted transition-colors duration-200 hover:border-brand hover:bg-brand hover:text-[color:var(--on-brand)] active:translate-y-px cursor-pointer"
              >
                Select file
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-start gap-5">
              <div className="flex w-full items-center gap-3 rounded-md border border-line bg-tint-2 p-3 text-left">
                <FileText className="h-5 w-5 flex-shrink-0 text-brand" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-txt">{file.name}</p>
                  <p className="font-mono text-micro text-txt-muted">{(file.size / 1024).toFixed(1)} KB</p>
                </div>
                <button
                  onClick={clearFile}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded text-txt-muted transition-colors hover:bg-tint-3 hover:text-txt active:translate-y-px cursor-pointer"
                  disabled={isUploading}
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              </div>
              <button onClick={handleUpload} disabled={isUploading} className="btn-primary w-full sm:w-auto">
                {isUploading ? (
                  <>
                    <svg className="h-4 w-4 animate-spin" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {slowWake ? 'Waking the server (~1 min)…' : 'Analyzing…'}
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
          Parsed on ExpenseEye's server and deleted when the session ends.
        </p>
      </div>

      {/* Terminal-style alert: a [SYS_ERR] readout in the danger signal, not a
          generic red box. Tag carries the color; the message stays high-contrast
          text-txt so it reads cleanly in both themes. */}
      {error && (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-md border border-danger/30 bg-danger/[0.07] px-4 py-3 font-mono text-data"
        >
          <span className="shrink-0 font-semibold uppercase tracking-wider text-danger">[SYS_ERR]</span>
          <p className="text-txt">{error}</p>
        </div>
      )}

      {mappingInfo && (
        <div className="rounded-md border border-success/25 bg-success/[0.06] p-4 text-sm">
          <div className="mb-3 flex items-center gap-2 font-medium text-success">
            <CheckCircle className="h-4 w-4" aria-hidden="true" />
            <p>Columns mapped</p>
          </div>
          <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
            <Mapped label="Date" value={mappingInfo.date_column} />
            <Mapped label="Date format" value={mappingInfo.date_format} />
            <Mapped label="Description" value={mappingInfo.description_column} />
            <Mapped label="Amount" value={mappingInfo.amount_pattern} />
            {mappingInfo.rows_skipped > 0 && (
              <div className="flex items-baseline gap-2">
                <dt className="text-txt-faint">Skipped</dt>
                <dd className="font-mono text-warning">{mappingInfo.rows_skipped} rows</dd>
              </div>
            )}
          </dl>
          {/* Honest exception list: which rows were dropped and why (P2-13). */}
          {mappingInfo.skipped_rows && mappingInfo.skipped_rows.length > 0 && (
            <ul className="mt-3 space-y-1 border-t border-success/20 pt-3 font-mono text-micro text-txt-muted">
              {mappingInfo.skipped_rows.slice(0, 5).map((s, i) => (
                <li key={i} className="flex gap-2">
                  <span className="shrink-0 text-warning">{s.row != null ? `row ${s.row}` : 'row —'}</span>
                  <span className="truncate">{s.reason}</span>
                </li>
              ))}
              {mappingInfo.rows_skipped > 5 && (
                <li className="text-txt-faint">+{mappingInfo.rows_skipped - 5} more…</li>
              )}
            </ul>
          )}
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
