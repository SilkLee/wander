import React, { useState } from 'react';
import { analyzeLog } from '../api/workflows';
import type { LogAnalysisResponse } from '../api/workflows';

const LOG_TYPES = ['build', 'deploy', 'runtime', 'generic'];

function LogAnalysisPage() {
  const [logContent, setLogContent] = useState('');
  const [logType, setLogType] = useState('generic');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LogAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    if (!logContent.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await analyzeLog({ log_content: logContent, log_type: logType });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  const severityColor: Record<string, string> = {
    critical: '#d32f2f',
    high: '#f44336',
    medium: '#ff9800',
    low: '#4caf50',
  };

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ margin: '0 0 8px', fontSize: 28 }}>Log Analysis</h1>
      <p style={{ margin: '0 0 24px', color: '#666', fontSize: 14 }}>
        Paste CI/CD logs to identify root causes and get fix suggestions
      </p>

      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <select
          value={logType}
          onChange={(e) => setLogType(e.target.value)}
          style={{
            padding: '8px 12px',
            borderRadius: 6,
            border: '1px solid #ccc',
            fontSize: 14,
          }}
        >
          {LOG_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <button
          onClick={handleAnalyze}
          disabled={loading || !logContent.trim()}
          style={{
            padding: '8px 24px',
            borderRadius: 6,
            border: 'none',
            backgroundColor: '#1976d2',
            color: '#fff',
            fontSize: 14,
            cursor: loading ? 'wait' : 'pointer',
            opacity: loading || !logContent.trim() ? 0.6 : 1,
          }}
        >
          {loading ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      <textarea
        value={logContent}
        onChange={(e) => setLogContent(e.target.value)}
        placeholder="Paste your log content here..."
        style={{
          width: '100%',
          minHeight: 200,
          padding: 12,
          borderRadius: 6,
          border: '1px solid #ccc',
          fontFamily: 'monospace',
          fontSize: 13,
          resize: 'vertical',
          boxSizing: 'border-box',
        }}
      />

      {error && (
        <div
          style={{
            marginTop: 16,
            padding: 12,
            borderRadius: 6,
            backgroundColor: '#fce4ec',
            color: '#c62828',
          }}
        >
          {error}
        </div>
      )}

      {result && (
        <div
          style={{
            marginTop: 24,
            background: '#fff',
            borderRadius: 8,
            padding: 24,
            border: '1px solid #e0e0e0',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
            <h2 style={{ margin: 0, fontSize: 18 }}>Analysis Result</h2>
            <span
              style={{
                padding: '4px 12px',
                borderRadius: 12,
                fontSize: 12,
                fontWeight: 600,
                color: '#fff',
                backgroundColor: severityColor[result.severity] || '#666',
              }}
            >
              {result.severity.toUpperCase()}
            </span>
          </div>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ margin: '0 0 4px', fontSize: 14, color: '#666' }}>Root Cause</h3>
            <p style={{ margin: 0 }}>{result.root_cause}</p>
          </div>

          <div style={{ marginBottom: 16 }}>
            <h3 style={{ margin: '0 0 4px', fontSize: 14, color: '#666' }}>Confidence</h3>
            <div
              style={{
                width: 200,
                height: 8,
                backgroundColor: '#e0e0e0',
                borderRadius: 4,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${result.confidence * 100}%`,
                  height: '100%',
                  backgroundColor: '#4caf50',
                  borderRadius: 4,
                }}
              />
            </div>
            <span style={{ fontSize: 12, color: '#666' }}>
              {(result.confidence * 100).toFixed(0)}%
            </span>
          </div>

          {result.suggested_fixes.length > 0 && (
            <div>
              <h3 style={{ margin: '0 0 8px', fontSize: 14, color: '#666' }}>Suggested Fixes</h3>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {result.suggested_fixes.map((fix, i) => (
                  <li key={`fix-${i}`} style={{ marginBottom: 4, fontSize: 14 }}>
                    {fix}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default LogAnalysisPage;
