import { useState, type DragEvent, type FormEvent } from 'react';
import type { AppConfig } from '../types/api';
import { CSV_FORMAT_HINT } from '../content/csvFormat';
import { Button } from './Button';

interface UploadSectionProps {
  config: AppConfig | null;
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  onSubmit: (file: File) => void;
}

function getFileExtension(fileName: string): string {
  const lastDot = fileName.lastIndexOf('.');
  return lastDot === -1 ? '' : fileName.slice(lastDot).toLowerCase();
}

function formatBytesAsMB(bytes: number): string {
  return (bytes / (1024 * 1024)).toFixed(1);
}

// Client-side pre-check against /config. This is a progressive enhancement —
// the server enforces the real limits regardless, so a missing/failed config
// fetch (config === null) just means we skip straight to letting the upload
// go and let the server respond with the authoritative error.
function validateFile(file: File, config: AppConfig): string | null {
  const extension = getFileExtension(file.name);
  if (!config.accepted_file_extensions.includes(extension)) {
    return `Please choose a ${config.accepted_file_extensions.join(', ')} file.`;
  }
  if (file.size > config.max_upload_bytes) {
    return `That file is too large. The limit is ${formatBytesAsMB(config.max_upload_bytes)} MB.`;
  }
  return null;
}

export function UploadSection({ config, selectedFile, onFileSelect, onSubmit }: UploadSectionProps) {
  const [localError, setLocalError] = useState<string | null>(null);
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const handleFileChange = (file: File | null) => {
    setLocalError(null);
    onFileSelect(null);

    if (!file) {
      return;
    }

    const validationError = config ? validateFile(file, config) : null;
    if (validationError) {
      setLocalError(validationError);
      return;
    }

    onFileSelect(file);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (selectedFile) {
      onSubmit(selectedFile);
    }
  };

  const handleDragOver = (event: DragEvent<HTMLElement>) => {
    event.preventDefault();
    setIsDraggingOver(true);
  };

  const handleDragLeave = () => setIsDraggingOver(false);

  const handleDrop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault();
    setIsDraggingOver(false);
    handleFileChange(event.dataTransfer.files?.[0] ?? null);
  };

  return (
    <section
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`rounded border p-4 transition-colors ${
        isDraggingOver ? 'border-brand-action bg-surface-overlay' : 'border-line-default bg-surface-raised'
      }`}
      aria-label="Upload your collection"
    >
      <form onSubmit={handleSubmit} className="flex flex-col items-start gap-2">
        <p className="text-sm font-medium text-ink-primary">Upload CSV</p>
        <label
          htmlFor="collection-upload"
          className="inline-flex w-fit items-center rounded bg-brand-action px-4 py-2 text-sm font-semibold text-ink-on-mana"
        >
          Choose File
        </label>
        <input
          id="collection-upload"
          type="file"
          accept=".csv"
          className="sr-only"
          onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
        />

        {selectedFile && (
          <p className="text-sm text-ink-secondary">
            Selected: <span className="text-ink-primary">{selectedFile.name}</span>
          </p>
        )}

        <p className="text-sm text-ink-secondary">
          {CSV_FORMAT_HINT} Or drag and drop a CSV file anywhere in this box.
        </p>

        {localError && (
          <p
            role="alert"
            className="rounded border-l-4 border-l-status-danger bg-surface-overlay p-2 text-sm font-medium text-ink-primary"
          >
            {localError}
          </p>
        )}

        <Button type="submit" disabled={!selectedFile} className="mt-2">
          Get Recommendations
        </Button>
      </form>
    </section>
  );
}
