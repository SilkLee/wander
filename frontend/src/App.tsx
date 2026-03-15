import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from './layout/AppLayout';

// Lazy-load page components for code splitting
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const LogAnalysisPage = lazy(() => import('./pages/LogAnalysisPage'));
const PrRiskPage = lazy(() => import('./pages/PrRiskPage'));
const CodeReviewPage = lazy(() => import('./pages/CodeReviewPage'));
const IncidentResponsePage = lazy(() => import('./pages/IncidentResponsePage'));
const DoraMetricsPage = lazy(() => import('./pages/DoraMetricsPage'));

const LoadingFallback = () => (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: '#666' }}>
    Loading…
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingFallback />}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/log-analysis" element={<LogAnalysisPage />} />
            <Route path="/pr-risk" element={<PrRiskPage />} />
            <Route path="/code-review" element={<CodeReviewPage />} />
            <Route path="/incident-response" element={<IncidentResponsePage />} />
            <Route path="/dora-metrics" element={<DoraMetricsPage />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

export default App;
