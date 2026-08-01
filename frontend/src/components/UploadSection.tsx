import { useState, type FormEvent } from 'react';
import type { AppConfig } from '../types/api';
import { CSV_FORMAT_HINT } from '../content/csvFormat';

interface UploadSectionProps {
  config: AppConfig | null;
  submitting: boolean;
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

export function UploadSection({ config, submitting, onSubmit }: UploadSectionProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const handleFileChange = (file: File | null) => {
    setLocalError(null);
    setSelectedFile(null);

    if (!file) {
      return;
    }

    const validationError = config ? validateFile(file, config) : null;
    if (validationError) {
      setLocalError(validationError);
      return;
    }

    setSelectedFile(file);
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (selectedFile) {
      onSubmit(selectedFile);
    }
  };

  return (
    <section className="upload-section" aria-label="Upload your collection">
      <form onSubmit={handleSubmit}>
        <label htmlFor="collection-upload">Collection CSV</label>
        <input
          id="collection-upload"
          type="file"
          accept=".csv"
          disabled={submitting}
          onChange={(event) => handleFileChange(event.target.files?.[0] ?? null)}
        />

        <p className="upload-hint">{CSV_FORMAT_HINT}</p>

        {localError && (
          <p className="upload-local-error" role="alert">
            {localError}
          </p>
        )}

        <button type="submit" disabled={!selectedFile || submitting}>
          {submitting ? 'Analyzing…' : 'Get Recommendations'}
        </button>
      </form>
    </section>
  );
}
