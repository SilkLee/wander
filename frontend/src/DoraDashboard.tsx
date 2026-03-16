import type { DORAMetrics } from './api/metrics';
import React, { useEffect, useState } from 'react';
import { fetchDoraMetrics } from './api/metrics';
import DoraMetricCard from './DoraMetricCard';
import DoraTrendChart from './DoraTrendChart';

function DoraDashboard() {
  const [metrics, setMetrics] = useState<DORAMetrics | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchDoraMetrics(controller.signal)
      .then((data) => setMetrics(data))
      .catch((err) => {
        if (!controller.signal.aborted) {
          console.error('DORA fetch failed:', err);
          setError(true);
        }
      });
    return () => controller.abort();
  }, []);

  return (
    <div style={{ padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <h1>DORA Metrics</h1>
      {error ? (
        <p>No data available</p>
      ) : metrics ? (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
            <DoraMetricCard name="Deployment Frequency" value={`${metrics.deployment_frequency}/day`} rating="Elite" />
            <DoraMetricCard name="Lead Time for Changes" value={`${metrics.lead_time} hrs`} rating="Elite" />
            <DoraMetricCard name="Change Failure Rate" value={`${(metrics.change_failure_rate * 100).toFixed(1)}%`} rating="Elite" />
            <DoraMetricCard name="Mean Time to Recovery" value={`${metrics.mttr} hrs`} rating="Elite" />
          </div>
          <DoraTrendChart
            title="Deployment Frequency Trend"
            data={metrics.trend.map((t) => t.deployment_frequency)}
          />
        </>
      ) : null}
    </div>
  );
}

export default DoraDashboard;
