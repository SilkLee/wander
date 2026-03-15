import React, { useState } from 'react';
import { executeWorkflow } from '../api/workflows';
import type { WorkflowExecutionResponse } from '../api/workflows';

function PrRiskPage() {
  const [diff, setDiff] = useState('');
  const [context, setContext] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<WorkflowExecutionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAssess = async () => {
    if (!diff.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await executeWorkflow({
        workflow_type: 'pr_risk',
        inputs: { diff, context: context || undefined },
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Assessment failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 32 }}>
      <h1 style={{ margin: '0 0 8px', fontSize: 28 }}>PR Risk Assessment</h1>
      <p style={{ margin: '0 0 24px', color: '#666', fontSize: 14 }}>
        Paste a PR diff to assess its risk level before merging
      </p>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 4, fontSize: 13, color: '#666' }}>
          PR Diff *
        </label>
        <textarea
          value={diff}
          onChange={(e) => setDiff(e.target.value)}
          placeholder="Paste PR diff here..."
          style={{
            width: '100%',
            minHeight: 180,
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
          Context (optional)
        </label>
        <textarea
          value={context}
          onChange={(e) => setContext(e.target.value)}
          placeholder="Additional context about the PR..."
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
        onClick={handleAssess}
        disabled={loading || !diff.trim()}
        style={{
          padding: '8px 24px',
          borderRadius: 6,
          border: 'none',
          backgroundColor: '#ff9800',
          color: '#fff',
          fontSize: 14,
          cursor: loading ? 'wait' : 'pointer',
          opacity: loading || !diff.trim() ? 0.6 : 1,
        }}
      >
        {loading ? 'Assessing...' : 'Assess Risk'}
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
            <h2 style={{ margin: 0, fontSize: 18 }}>Assessment Result</h2>
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

export default PrRiskPage;
