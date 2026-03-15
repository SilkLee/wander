import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from './layout/AppLayout';
import DashboardPage from './pages/DashboardPage';
import LogAnalysisPage from './pages/LogAnalysisPage';
import PrRiskPage from './pages/PrRiskPage';
import CodeReviewPage from './pages/CodeReviewPage';
import IncidentResponsePage from './pages/IncidentResponsePage';
import DoraMetricsPage from './pages/DoraMetricsPage';

function App() {
  return (
    <BrowserRouter>
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
    </BrowserRouter>
  );
}

export default App;
