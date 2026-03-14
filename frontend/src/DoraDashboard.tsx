import React from 'react';
import DoraMetricCard from './DoraMetricCard';
import DoraTrendChart from './DoraTrendChart';

function DoraDashboard() {
  return (
    <div style={{ padding: 24, fontFamily: 'system-ui, sans-serif' }}>
      <h1>DORA Metrics</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 24 }}>
        <DoraMetricCard name="Deployment Frequency" value="3.2/day" rating="Elite" />
        <DoraMetricCard name="Lead Time for Changes" value="2.5 hrs" rating="Elite" />
        <DoraMetricCard name="Change Failure Rate" value="4.2%" rating="Elite" />
        <DoraMetricCard name="Mean Time to Recovery" value="0.8 hrs" rating="Elite" />
      </div>
      <DoraTrendChart title="Deployment Frequency Trend" data={[2.1, 2.5, 2.8, 3.0, 3.2, 3.1, 3.2]} />
    </div>
  );
}

export default DoraDashboard;
