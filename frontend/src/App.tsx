import { useEffect, useState } from 'react';
import './App.css';
import { APIError, fetchConfig, submitCollection } from './api/client';
import type { APIErrorDetail, AppConfig, RecommendationResponse } from './types/api';
import { Header } from './components/Header';
import { UploadSection } from './components/UploadSection';
import { LoadingState } from './components/LoadingState';
import { ErrorState } from './components/ErrorState';

type ViewState = 'idle' | 'loading' | 'results' | 'error';

const NETWORK_ERROR_DETAIL: APIErrorDetail = {
  code: 'NETWORK_ERROR',
  message: 'Could not reach the recommendation service. Check your connection and try again.',
  unmatched_names: [],
  warnings: [],
};

function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [viewState, setViewState] = useState<ViewState>('idle');
  const [responseData, setResponseData] = useState<RecommendationResponse | null>(null);
  const [errorInfo, setErrorInfo] = useState<APIErrorDetail | null>(null);

  useEffect(() => {
    // Progressive enhancement only — the server enforces the real limits, so a
    // failed config fetch just means the upload form skips client-side pre-checks.
    fetchConfig()
      .then(setConfig)
      .catch(() => setConfig(null));
  }, []);

  const handleSubmit = async (file: File) => {
    setViewState('loading');
    setErrorInfo(null);

    try {
      const result = await submitCollection(file);
      setResponseData(result);
      setViewState('results');
    } catch (error) {
      setErrorInfo(error instanceof APIError ? error.detail : NETWORK_ERROR_DETAIL);
      setViewState('error');
    }
  };

  return (
    <div className="app">
      <Header />
      <main>
        {(viewState === 'idle' || viewState === 'error') && (
          <UploadSection config={config} submitting={false} onSubmit={handleSubmit} />
        )}

        {viewState === 'loading' && <LoadingState />}

        {viewState === 'error' && errorInfo && <ErrorState error={errorInfo} />}

        {viewState === 'results' && responseData && (
          // Placeholder for the next section (ResultsSection) — recommendation
          // cards, theme breakdown, and supporting-card panels land here next.
          <section className="results-placeholder">
            <p>
              Found {responseData.recommendations.length} recommendation(s) from{' '}
              {responseData.unique_cards} unique cards ({responseData.total_cards} total).
            </p>
            <p>Top themes: {responseData.top_themes.join(', ') || 'none detected'}</p>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
