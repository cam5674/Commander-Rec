import { useEffect, useRef, useState } from 'react';
import { APIError, fetchConfig, submitCollection } from './api/client';
import type { APIErrorDetail, AppConfig, RecommendationResponse } from './types/api';
import { Header } from './components/Header';
import { UploadSection } from './components/UploadSection';
import { LoadingState } from './components/LoadingState';
import { ErrorState } from './components/ErrorState';
import { RecommendationCard } from './components/RecommendationCard';
import { UnmatchedCardsNotice } from './components/UnmatchedCardsNotice';
import { EmptyRecommendations } from './components/EmptyRecommendations';
import { Button } from './components/Button';
import { formatThemeList, getThemeLabel } from './content/themeLabels';
import { buildRecommendationPresentations } from './content/recommendationPresentation';

type ViewState = 'idle' | 'loading' | 'results' | 'error';

const UNMATCHED_EMPHASIS_RATIO = 0.25;

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
  const [themeFilter, setThemeFilter] = useState<string | null>(null);
  const resultsHeadingRef = useRef<HTMLHeadingElement>(null);
  const errorContainerRef = useRef<HTMLDivElement>(null);

  // Lifted out of UploadSection so it survives that component unmounting
  // during the loading state — otherwise a server error forced re-picking
  // the same file to retry, since the child's local state was wiped.
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    // Progressive enhancement only — the server enforces the real limits, so a
    // failed config fetch just means the upload form skips client-side pre-checks.
    fetchConfig()
      .then(setConfig)
      .catch(() => setConfig(null));
  }, []);

  useEffect(() => {
    if (viewState === 'results') {
      resultsHeadingRef.current?.focus();
    } else if (viewState === 'error') {
      errorContainerRef.current?.focus();
    }
  }, [viewState]);

  const handleSubmit = async (file: File) => {
    setViewState('loading');
    setErrorInfo(null);

    try {
      const result = await submitCollection(file);
      setResponseData(result);
      setThemeFilter(null);
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
    setThemeFilter(null);
    setSelectedFile(null);
  };

  const handleThemeClick = (theme: string) => {
    setThemeFilter((current) => (current === theme ? null : theme));
  };

  const visibleRecommendations = responseData
    ? themeFilter
      ? responseData.recommendations.filter((commander) => commander.matching_themes.includes(themeFilter))
      : responseData.recommendations
    : [];
  const recommendationPresentations = buildRecommendationPresentations(
    visibleRecommendations,
    themeFilter,
  );

  const hasCollectionNotices = responseData
    ? responseData.unmatched_names.length > 0 || responseData.warnings.length > 0
    : false;
  const unmatchedComparisonCount = responseData
    ? responseData.unique_cards + responseData.unmatched_names.length
    : 0;
  const shouldEmphasizeUnmatched = responseData
    ? unmatchedComparisonCount > 0
      && responseData.unmatched_names.length / unmatchedComparisonCount
        >= UNMATCHED_EMPHASIS_RATIO
    : false;

  const containerWidthClass =
    viewState === 'results'
      ? 'max-w-2xl md:max-w-3xl lg:max-w-5xl xl:max-w-6xl 2xl:max-w-7xl'
      : 'max-w-2xl';

  return (
    <div className={`mx-auto flex flex-col gap-6 px-4 py-6 ${containerWidthClass}`}>
      <Header centered={viewState === 'results'} />
      <main className="flex flex-col gap-4">
        {(viewState === 'idle' || viewState === 'error') && (
          <UploadSection
            config={config}
            selectedFile={selectedFile}
            onFileSelect={setSelectedFile}
            onSubmit={handleSubmit}
          />
        )}

        {viewState === 'loading' && <LoadingState />}

        {viewState === 'error' && errorInfo && (
          <div ref={errorContainerRef} tabIndex={-1} aria-label="Collection upload error">
            <ErrorState error={errorInfo} />
          </div>
        )}

        {viewState === 'results' && responseData && (
          <section className="flex flex-col gap-4">
            <h2 ref={resultsHeadingRef} tabIndex={-1} className="sr-only">
              Commander recommendations
            </h2>

            <div className="flex justify-center lg:sticky lg:top-4 lg:z-30">
              <div className="flex max-w-full flex-col items-center gap-2 rounded border border-line-default bg-surface-base/95 p-3 text-center shadow-lg">
                <Button type="button" onClick={handleReset} className="shrink-0">
                  Upload Another Collection
                </Button>
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
              </div>
            </div>

            {/* The sidebar stays stacked through md: two cards plus a sidebar
                would make each horizontal card too narrow at tablet widths. */}
            <div
              className={`flex flex-col gap-6 ${
                hasCollectionNotices ? 'lg:flex-row lg:items-start lg:gap-8' : ''
              }`}
            >
              {hasCollectionNotices && (
                <aside className="flex flex-col gap-4 lg:order-2 lg:w-64 lg:shrink-0">
                  <UnmatchedCardsNotice
                    unmatchedNames={responseData.unmatched_names}
                    warnings={responseData.warnings}
                    defaultExpanded={shouldEmphasizeUnmatched}
                    emphasized={shouldEmphasizeUnmatched}
                  />
                </aside>
              )}

              <div
                className={`min-w-0 flex-1 lg:order-1 ${
                  hasCollectionNotices ? '' : 'mx-auto w-full max-w-5xl'
                }`}
              >
                {themeFilter && (
                  <div className="mb-3 flex items-center gap-2 text-xs text-ink-secondary">
                    <span>Filtering by {getThemeLabel(themeFilter)}</span>
                    <button
                      type="button"
                      onClick={() => setThemeFilter(null)}
                      className="font-medium text-brand-action"
                    >
                      Clear
                    </button>
                  </div>
                )}

                {responseData.recommendations.length === 0 ? (
                  <EmptyRecommendations />
                ) : (
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    {visibleRecommendations.map((commander, index) => (
                      <div
                        key={commander.oracle_id}
                        className="h-full animate-fade-in-up motion-reduce:animate-none"
                        style={{ animationDelay: `${Math.min(index * 40, 400)}ms` }}
                      >
                        <RecommendationCard
                          {...commander}
                          rank={responseData.recommendations.indexOf(commander) + 1}
                          presentation={recommendationPresentations[index]}
                          selectedTheme={themeFilter}
                          onThemeClick={handleThemeClick}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
