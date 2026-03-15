import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';

const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/log-analysis', label: 'Log Analysis', icon: '📋' },
  { path: '/pr-risk', label: 'PR Risk', icon: '⚠️' },
  { path: '/code-review', label: 'Code Review', icon: '🔍' },
  { path: '/incident-response', label: 'Incident Response', icon: '🚨' },
  { path: '/dora-metrics', label: 'DORA Metrics', icon: '📈' },
];

function AppLayout() {
  return (
    <div style={{ display: 'flex', height: '100vh', fontFamily: 'system-ui, sans-serif' }}>
      {/* Sidebar */}
      <nav
        style={{
          width: 240,
          backgroundColor: '#1a1a2e',
          color: '#fff',
          display: 'flex',
          flexDirection: 'column',
          padding: '16px 0',
          flexShrink: 0,
        }}
      >
        <div style={{ padding: '0 16px 24px', borderBottom: '1px solid #333' }}>
          <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>WorkflowAI</h1>
          <span style={{ fontSize: 12, color: '#888' }}>DevOps Intelligence</span>
        </div>
        <div style={{ flex: 1, paddingTop: 8 }}>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '10px 16px',
                color: isActive ? '#fff' : '#aaa',
                backgroundColor: isActive ? '#16213e' : 'transparent',
                textDecoration: 'none',
                fontSize: 14,
                borderLeft: isActive ? '3px solid #4361ee' : '3px solid transparent',
              })}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main style={{ flex: 1, overflow: 'auto', backgroundColor: '#f5f5f5' }}>
        <Outlet />
      </main>
    </div>
  );
}

export default AppLayout;
