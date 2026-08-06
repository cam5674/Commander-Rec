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
import { TextLink } from './components/TextLink';
import { formatThemeList, getThemeLabel } from './content/themeLabels';
import { buildRecommendationPresentations } from './content/recommendationPresentation';

type ViewState = 'idle' | 'loading' | 'results' | 'error';

const UNMATCHED_EMPHASIS_RATIO = 0.25;
const DEFAULT_VISIBLE_COUNT = 10;

const NETWORK_ERROR_DETAIL: APIErrorDetail = {
  code: 'NETWORK_ERROR',
  message: 'Could not reach the recommendation service. Check your connection and try again.',
  unmatched_names: [],
  warnings: [],
};

// Bundled as a static frontend asset (frontend/public/samples), not served
// by the API — fetched client-side and funneled through the exact same
// submitCollection() request as a user-selected file.
const SAMPLE_CSV_PATH = '/samples/showcase.csv';
const SAMPLE_CSV_FILENAME = 'showcase-collection.csv';

const SAMPLE_LOAD_ERROR_DETAIL: APIErrorDetail = {
  code: 'SAMPLE_LOAD_ERROR',
  message: 'Could not load the sample collection. Try again, or upload your own CSV.',
  unmatched_names: [],
  warnings: [],
};

async function loadSampleFile(): Promise<File> {
  const response = await fetch(SAMPLE_CSV_PATH);
  if (!response.ok) {
    throw new Error(`Failed to load sample CSV (${response.status})`);
  }
  const blob = await response.blob();
  return new File([blob], SAMPLE_CSV_FILENAME, { type: 'text/csv' });
}

function App() {
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [viewState, setViewState] = useState<ViewState>('idle');
  const [responseData, setResponseData] = useState<RecommendationResponse | null>(null);
  const [errorInfo, setErrorInfo] = useState<APIErrorDetail | null>(null);
  const [themeFilter, setThemeFilter] = useState<string | null>(null);
  const [visibleCount, setVisibleCount] = useState(DEFAULT_VISIBLE_COUNT);
  const [isSampleResult, setIsSampleResult] = useState(false);
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

  // Shared by both the real upload and the sample trigger — same request,
  // same loading/error/results handling either way. The only thing that
  // differs between the two callers is how the File object was obtained.
  const submitFile = async (file: File, isSample: boolean) => {
    try {
      const result = await submitCollection(file);
      setResponseData(result);
      setThemeFilter(null);
      setVisibleCount(DEFAULT_VISIBLE_COUNT);
      setIsSampleResult(isSample);
      setViewState('results');
    } catch (error) {
      setErrorInfo(error instanceof APIError ? error.detail : NETWORK_ERROR_DETAIL);
      setViewState('error');
    }
  };

  const handleSubmit = async (file: File) => {
    setViewState('loading');
    setErrorInfo(null);
    await submitFile(file, false);
  };

  const handleTrySample = async () => {
    // Flips to 'loading' before anything async runs, same as handleSubmit —
    // UploadSection (and this trigger with it) unmounts on the next render,
    // which is what guards against a second click firing mid-request rather
    // than a dedicated isSubmitting flag.
    setViewState('loading');
    setErrorInfo(null);

    try {
      const sampleFile = await loadSampleFile();
      await submitFile(sampleFile, true);
    } catch {
      // Only reached if fetching the bundled asset itself failed —
      // submitFile handles its own submission errors internally.
      setErrorInfo(SAMPLE_LOAD_ERROR_DETAIL);
      setViewState('error');
    }
  };

  const handleReset = () => {
    setViewState('idle');
    setResponseData(null);
    setErrorInfo(null);
    setThemeFilter(null);
    setVisibleCount(DEFAULT_VISIBLE_COUNT);
    setIsSampleResult(false);
    setSelectedFile(null);
  };

  const handleThemeClick = (theme: string) => {
    setThemeFilter((current) => (current === theme ? null : theme));
    // Filtering always shows every matching commander from the full result
    // set (not just what's currently revealed), so the browse cutoff is
    // irrelevant while a filter is active. Reset it so clearing the filter
    // lands back on the standard 10-card default rather than wherever
    // "show more" was left.
    setVisibleCount(DEFAULT_VISIBLE_COUNT);
  };

  const handleShowMore = () => {
    if (responseData) {
      setVisibleCount(responseData.recommendations.length);
    }
  };

  // Theme filtering always searches the full pool the API returned (up to
  // 20), not just what's currently revealed — a user drilling into a theme
  // tag expects every match, not just the ones the browse cutoff happened
  // to show. The 10-card default and "show more" are purely a browse
  // convenience for the unfiltered view.
  const visibleRecommendations = responseData
    ? themeFilter
      ? responseData.recommendations.filter((commander) => commander.matching_themes.includes(themeFilter))
      : responseData.recommendations
    : [];
  const displayedRecommendations = themeFilter
    ? visibleRecommendations
    : visibleRecommendations.slice(0, visibleCount);
  const recommendationPresentations = buildRecommendationPresentations(
    displayedRecommendations,
    themeFilter,
  );
  const hasMoreToShow = responseData
    ? !themeFilter && visibleCount < responseData.recommendations.length
    : false;

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
            onTrySample={handleTrySample}
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

            {/* This wrapper spans the full row width so its child can be
                centered, but at lg: it's also `sticky` — meaning that full
                width becomes a real, stacked-above-the-grid hit-testable box
                as the page scrolls, even though only the centered child is
                painted. Without `pointer-events-none` here, the transparent
                margins on either side of that child silently swallow clicks
                on whatever card row happens to scroll underneath (confirmed
                via elementFromPoint, not just visually) — `pointer-events-
                auto` on the child alone restores clickability there. */}
            <div className="pointer-events-none flex justify-center lg:sticky lg:top-4 lg:z-30">
              <div className="pointer-events-auto flex max-w-full flex-col items-center gap-2 rounded border border-line-default bg-surface-base/95 p-3 text-center shadow-lg">
                <Button type="button" onClick={handleReset} className="shrink-0">
                  Upload Another Collection
                </Button>
                <div>
                  {isSampleResult && (
                    <p className="mb-1">
                      <span className="rounded bg-surface-overlay px-2 py-1 text-xs text-ink-secondary">
                        Sample collection
                      </span>
                    </p>
                  )}
                  <p className="text-sm text-ink-secondary">
                    Found {responseData.recommendations.length} recommendation(s) from{' '}
                    {responseData.unique_cards} unique cards ({responseData.total_cards} total).
                  </p>
                  <p className="text-sm text-ink-secondary">
                    Top themes:{' '}
                    {responseData.top_themes.length > 0
                      ? formatThemeList(responseData.top_themes)
                      : 'none detected'}
                  </p>
                  {!themeFilter && (
                    <p className="text-xs text-ink-muted">
                      Tip: click a theme tag on any card to filter by it.
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* The sidebar stays stacked through md: two cards plus a sidebar
                would make each horizontal card too narrow at tablet widths.
                Main content renders before the aside in the DOM (rather than
                using lg:order-* to visually reorder them) so tab order and
                reading order always agree with what's on screen at every
                breakpoint — the recommendation grid is the focal content and
                the notices sidebar is secondary, both in reading priority
                and in this element order. This is a deliberate, minimal
                change from the prior stacked-mobile arrangement (which had
                the aside above the grid, sourced from the old order-driven
                DOM position) to one consistent order everywhere. */}
            <div
              className={`flex flex-col gap-6 ${
                hasCollectionNotices ? 'lg:flex-row lg:items-start lg:gap-8' : ''
              }`}
            >
              <div
                className={`min-w-0 flex-1 ${
                  hasCollectionNotices ? '' : 'mx-auto w-full max-w-5xl'
                }`}
              >
                {themeFilter && (
                  <div className="mb-3 flex items-center gap-2 text-xs text-ink-secondary">
                    <span>Filtering by {getThemeLabel(themeFilter)}</span>
                    <TextLink onClick={() => setThemeFilter(null)}>Clear</TextLink>
                  </div>
                )}

                {responseData.recommendations.length === 0 ? (
                  <EmptyRecommendations topThemes={responseData.top_themes} />
                ) : (
                  <>
                    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                      {displayedRecommendations.map((commander, index) => (
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

                    {hasMoreToShow && (
                      <div className="mt-4 flex justify-center">
                        <Button type="button" onClick={handleShowMore}>
                          Show {responseData.recommendations.length - visibleCount} more
                        </Button>
                      </div>
                    )}
                  </>
                )}
              </div>

              {hasCollectionNotices && (
                <aside className="flex flex-col gap-4 lg:w-64 lg:shrink-0">
                  <UnmatchedCardsNotice
                    unmatchedNames={responseData.unmatched_names}
                    warnings={responseData.warnings}
                    defaultExpanded={shouldEmphasizeUnmatched}
                    emphasized={shouldEmphasizeUnmatched}
                  />
                </aside>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
