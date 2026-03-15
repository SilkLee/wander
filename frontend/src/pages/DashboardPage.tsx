import React from 'react';
import { Link } from 'react-router-dom';

const WORKFLOWS = [
  {
    name: 'Log Analysis',
    path: '/log-analysis',
    description: 'Analyze build/deploy logs for failures and root causes',
    status: 'available',
    icon: '📋',
    color: '#2196f3',
  },
  {
    name: 'PR Risk Assessment',
    path: '/pr-risk',
    description: 'Assess risk level of pull requests before merging',
    status: 'available',
    icon: '⚠️',
    color: '#ff9800',
  },
  {
    name: 'Code Review',
    path: '/code-review',
    description: 'AI-powered code review with actionable feedback',
    status: 'available',
    icon: '🔍',
    color: '#9c27b0',
  },
  {
    name: 'Incident Response',
    path: '/incident-response',
    description: 'Automated incident triage and remediation guidance',
    status: 'available',
    icon: '🚨',
    color: '#f44336',
  },
  {
    name: 'DORA Metrics',
    path: '/dora-metrics',
    description: 'Track deployment frequency, lead time, CFR, and MTTR',
    status: 'available',
    icon: '📈',
    color: '#4caf50',
  },
];

function DashboardPage() {
  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ margin: '0 0 8px', fontSize: 28 }}>Dashboard</h1>
      <p style={{ margin: '0 0 32px', color: '#666', fontSize: 14 }}>
        AI-powered DevOps workflow automation platform
      </p>

      {/* Status Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 16,
          marginBottom: 32,
        }}
      >
        <div
          style={{
            background: '#fff',
            borderRadius: 8,
            padding: 20,
            border: '1px solid #e0e0e0',
          }}
        >
          <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Total Workflows</div>
          <div style={{ fontSize: 32, fontWeight: 700 }}>5</div>
        </div>
        <div
          style={{
            background: '#fff',
            borderRadius: 8,
            padding: 20,
            border: '1px solid #e0e0e0',
          }}
        >
          <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Available</div>
          <div style={{ fontSize: 32, fontWeight: 700, color: '#4caf50' }}>5</div>
        </div>
        <div
          style={{
            background: '#fff',
            borderRadius: 8,
            padding: 20,
            border: '1px solid #e0e0e0',
          }}
        >
          <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Services Running</div>
          <div style={{ fontSize: 32, fontWeight: 700, color: '#2196f3' }}>6</div>
        </div>
      </div>

      {/* Workflow Cards */}
      <h2 style={{ margin: '0 0 16px', fontSize: 18 }}>Workflows</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
        {WORKFLOWS.map((wf) => (
          <Link
            key={wf.path}
            to={wf.path}
            style={{
              textDecoration: 'none',
              color: 'inherit',
              background: '#fff',
              borderRadius: 8,
              padding: 20,
              border: '1px solid #e0e0e0',
              display: 'flex',
              gap: 16,
              alignItems: 'flex-start',
              transition: 'box-shadow 0.2s',
            }}
          >
            <span style={{ fontSize: 28 }}>{wf.icon}</span>
            <div>
              <h3 style={{ margin: '0 0 4px', fontSize: 16 }}>{wf.name}</h3>
              <p style={{ margin: '0 0 8px', fontSize: 13, color: '#666' }}>{wf.description}</p>
              <span
                style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 12,
                  backgroundColor: wf.status === 'available' ? '#e8f5e9' : '#fff3e0',
                  color: wf.status === 'available' ? '#2e7d32' : '#e65100',
                }}
              >
                {wf.status}
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default DashboardPage;
