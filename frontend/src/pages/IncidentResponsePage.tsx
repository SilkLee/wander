import React, { useState } from 'react';
import { executeWorkflow } from '../api/workflows';
import type { WorkflowExecutionResponse } from '../api/workflows';

function IncidentResponsePage() {
  const [logContent, setLogContent] = useState('');
  const [alerts, setAlerts] = useState('');
  const [deployContext, setDeployContext] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WorkflowExecutionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleTriage = async () => {
    if (!logContent.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      let parsedAlerts: unknown = undefined;
      if (alerts.trim()) {
        try {
          parsedAlerts = JSON.parse(alerts);
        } catch {
          parsedAlerts = alerts;
        }
      }
      const data = await executeWorkflow({
        workflow_type: 'incident_response',
        inputs: {
          log_content: logContent,
          alerts: parsedAlerts,
          deploy_context: deployContext || undefined,
        },
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Triage failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ margin: '0 0 8px', fontSize: 28 }}>Incident Response</h1>
      <p style={{ margin: '0 0 24px', color: '#666', fontSize: 14 }}>
        Automated incident triage with log parsing, impact assessment, and remediation
      </p>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontSize: 13, color: '#666' }}>
          Log Content *
        </label>
        <textarea
          value={logContent}
          onChange={(e) => setLogContent(e.target.value)}
          placeholder="Paste incident logs here..."
          style={{
            width: '100%',
            minHeight: 160,
            padding: 12,
            borderRadius: 6,
            border: '1px solid #ccc',
            fontFamily: 'monospace',
            fontSize: 13,
            resize: 'vertical',
            boxSizing: 'border-box',
          }}
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontSize: 13, color: '#666' }}>
          Alerts JSON (optional)
        </label>
        <textarea
          value={alerts}
          onChange={(e) => setAlerts(e.target.value)}
          placeholder='[{"alert": "CPU > 90%", "source": "prometheus"}]'
          style={{
            width: '100%',
            minHeight: 80,
            padding: 12,
            borderRadius: 6,
            border: '1px solid #ccc',
            fontFamily: 'monospace',
            fontSize: 13,
            resize: 'vertical',
            boxSizing: 'border-box',
          }}
        />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontSize: 13, color: '#666' }}>
          Deploy Context (optional)
        </label>
        <textarea
          value={deployContext}
          onChange={(e) => setDeployContext(e.target.value)}
          placeholder="Recent deployment details..."
          style={{
            width: '100%',
            minHeight: 80,
            padding: 12,
            borderRadius: 6,
            border: '1px solid #ccc',
            fontSize: 13,
            resize: 'vertical',
            boxSizing: 'border-box',
          }}
        />
      </div>

      <button
        onClick={handleTriage}
        disabled={loading || !logContent.trim()}
        style={{
          padding: '8px 24px',
          borderRadius: 6,
          border: 'none',
          backgroundColor: '#f44336',
          color: '#fff',
          fontSize: 14,
          cursor: loading ? 'wait' : 'pointer',
          opacity: loading || !logContent.trim() ? 0.6 : 1,
        }}
      >
        {loading ? 'Triaging...' : 'Triage Incident'}
      </button>

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
            <h2 style={{ margin: 0, fontSize: 18 }}>Triage Result</h2>
            <span
              style={{
                padding: '4px 12px',
                borderRadius: 12,
                fontSize: 12,
                fontWeight: 600,
                color: '#fff',
                backgroundColor: result.status === 'completed' ? '#4caf50' : '#f44336',
              }}
            >
              {result.status}
            </span>
          </div>
          {result.error && (
            <p style={{ color: '#c62828' }}>Error: {result.error}</p>
          )}
          <div style={{ marginBottom: 8, fontSize: 13, color: '#666' }}>
            Execution time: {result.execution_time.toFixed(2)}s
          </div>
          <pre
            style={{
              background: '#f5f5f5',
              padding: 16,
              borderRadius: 6,
              overflow: 'auto',
              fontSize: 13,
              maxHeight: 400,
            }}
          >
            {JSON.stringify(result.outputs, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default IncidentResponsePage;
