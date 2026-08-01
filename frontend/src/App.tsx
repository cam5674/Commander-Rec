import { useEffect, useState } from 'react';
import { APIError, fetchConfig, submitCollection } from './api/client';
import type { APIErrorDetail, AppConfig, RecommendationResponse } from './types/api';
import { Header } from './components/Header';
import { UploadSection } from './components/UploadSection';
import { LoadingState } from './components/LoadingState';
import { ErrorState } from './components/ErrorState';
import { RecommendationCard } from './components/RecommendationCard';
import { UnmatchedCardsNotice } from './components/UnmatchedCardsNotice';
import { formatThemeList } from './content/themeLabels';

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

  const handleReset = () => {
    setViewState('idle');
    setResponseData(null);
    setErrorInfo(null);
  };

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-6">
      <Header />
      <main className="flex flex-col gap-4">
        {(viewState === 'idle' || viewState === 'error') && (
          <UploadSection config={config} submitting={false} onSubmit={handleSubmit} />
        )}

        {viewState === 'loading' && <LoadingState />}

        {viewState === 'error' && errorInfo && <ErrorState error={errorInfo} />}

        {viewState === 'results' && responseData && (
          <section className="flex flex-col gap-2">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-xs text-ink-muted">
                  Found {responseData.recommendations.length} recommendation(s) from{' '}
                  {responseData.unique_cards} unique cards ({responseData.total_cards} total).
                </p>
                <p className="text-xs text-ink-muted">
                  Top themes:{' '}
                  {responseData.top_themes.length > 0
                    ? formatThemeList(responseData.top_themes)
                    : 'none detected'}
                </p>
              </div>

              <button
                type="button"
                onClick={handleReset}
                className="shrink-0 rounded bg-brand-action px-4 py-2 text-sm font-semibold text-ink-on-mana"
              >
                Upload Another Collection
              </button>
            </div>

            {(responseData.unmatched_names.length > 0 || responseData.warnings.length > 0) && (
              <UnmatchedCardsNotice
                unmatchedNames={responseData.unmatched_names}
                warnings={responseData.warnings}
              />
            )}

            <div className="mt-4 flex flex-col gap-3">
              {responseData.recommendations.map((commander) => (
                <RecommendationCard key={commander.oracle_id} {...commander} />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
